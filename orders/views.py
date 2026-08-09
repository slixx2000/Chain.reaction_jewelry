import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from cart.cart import Cart
from . import bila, services
from .forms import CheckoutForm
from .models import Order

logger = logging.getLogger(__name__)

SESSION_ORDERS_KEY = 'order_refs'


def _remember(request, order):
    """Let a guest come back to their own order without logging in."""
    refs = request.session.get(SESSION_ORDERS_KEY, [])
    if order.reference not in refs:
        request.session[SESSION_ORDERS_KEY] = ([order.reference] + refs)[:20]


def _get_visible_order(request, reference):
    order = get_object_or_404(Order, reference=reference)
    owns_it = order.user_id and order.user_id == request.user.id
    if owns_it or reference in request.session.get(SESSION_ORDERS_KEY, []):
        return order
    raise Http404


def checkout(request):
    cart = Cart(request)
    lines = list(cart)

    if not lines:
        messages.error(request, 'Your bag is empty.')
        return redirect('cart:cart_summary')

    sold = [line['item'].name for line in lines if line['item'].is_sold]
    if sold:
        messages.error(request, f'No longer available: {", ".join(sold)}. Please remove it from your bag.')
        return redirect('cart:cart_summary')

    form = CheckoutForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        try:
            order = services.create_order(
                cart,
                user=request.user,
                operator=form.operator,
                **form.cleaned_data,
            )
        except services.OutOfStock as exc:
            messages.error(request, f'Sold while you were checking out: {exc}. Please remove it from your bag.')
            return redirect('cart:cart_summary')
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('cart:cart_summary')

        _remember(request, order)

        try:
            services.start_payment(order)
        except bila.BilaError as exc:
            logger.error('Payment start failed for %s: %s', order.reference, exc)
            order.status = Order.Status.FAILED
            order.failure_reason = 'We could not reach the payment provider. Nothing was charged.'
            order.save(update_fields=['status', 'failure_reason', 'updated_at'])

        return redirect('orders:status', reference=order.reference)

    return render(request, 'orders/checkout.html', {
        'form': form,
        'cart_items': lines,
        'total': cart.get_total_price(),
    })


def order_status(request, reference):
    order = _get_visible_order(request, reference)
    order = services.refresh_from_bila(order)

    if order.status == Order.Status.PAID:
        cart = Cart(request)
        if len(cart):
            cart.clear()

    return render(request, 'orders/order_status.html', {'order': order})


def order_state(request, reference):
    """Polled by the status page so it can settle without a manual refresh."""
    order = services.refresh_from_bila(_get_visible_order(request, reference))
    return JsonResponse({
        'status': order.status,
        'settled': order.is_settled,
        'label': order.get_status_display(),
    })


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'orders/history.html', {'orders': orders})


@csrf_exempt
@require_POST
def bila_webhook(request):
    """Bila pings us; we verify the signature then ask Bila what actually happened.

    The webhook body is only a trigger — the collection status endpoint is the
    source of truth, so a malformed or replayed body cannot mark an order paid.
    """
    if not bila.verify_webhook(
        request.body,
        request.headers.get('X-Bila-Timestamp'),
        request.headers.get('X-Bila-Signature'),
    ):
        logger.warning('Rejected Bila webhook with a bad signature')
        return JsonResponse({'detail': 'invalid signature'}, status=401)

    try:
        payload = json.loads(request.body)
    except ValueError:
        return JsonResponse({'detail': 'invalid json'}, status=400)

    reference = _find_reference(payload)
    if not reference:
        logger.warning('Bila webhook had no reference: %s', payload)
        return JsonResponse({'detail': 'no reference'}, status=400)

    order = Order.objects.filter(reference=reference).first()
    if order:
        services.refresh_from_bila(order)

    return JsonResponse({'detail': 'ok'})


def _find_reference(payload):
    """Bila's webhook body shape is not pinned down in the docs — look around."""
    seen = payload
    for _ in range(3):
        if not isinstance(seen, dict):
            return None
        if isinstance(seen.get('reference'), str):
            return seen['reference']
        seen = seen.get('data')
    return None
