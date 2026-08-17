import hmac
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

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


@ratelimit(key='ip', rate='5/h', method='POST', block=True)
@ratelimit(key='post:phone', rate='3/h', method='POST', block=True)
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


@ratelimit(key='ip', rate='30/m', block=True)
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


@ratelimit(key='ip', rate='120/m', method='POST', block=True)
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

    references, collection_ids = _find_identifiers(payload)
    if not references and not collection_ids:
        logger.warning('Bila webhook had no usable identifier: %s', payload)
        return JsonResponse({'detail': 'no reference'}, status=400)

    order = (
        Order.objects.filter(reference__in=references).first()
        or Order.objects.filter(bila_collection_id__in=collection_ids).first()
    )
    # An identifier we don't recognise is still acknowledged — a 4xx would only
    # make Bila retry a webhook that can never match.
    if order:
        services.refresh_from_bila(order)
    return JsonResponse({'detail': 'ok'})


def _find_identifiers(payload):
    """Bila names the order differently per environment: sandbox bodies carry
    our `reference`, live bodies only the collection `id` — collect both."""
    references, collection_ids = [], []
    seen = payload
    for _ in range(3):
        if not isinstance(seen, dict):
            break
        if isinstance(seen.get('reference'), str):
            references.append(seen['reference'])
        for key in ('id', 'collectionId', 'transactionId'):
            if isinstance(seen.get(key), str) and seen[key]:
                collection_ids.append(seen[key])
        seen = seen.get('data')
    return references, collection_ids


@ratelimit(key='ip', rate='10/m', method='POST', block=True)
@csrf_exempt
@require_POST
def reconcile_pending(request):
    """Settle orders whose webhook never arrived. Called by an external scheduler.

    Same work as `manage.py reconcile_orders`, over HTTP, because free hosts
    vary in whether they offer cron. Authenticated with a shared secret in the
    `X-Cron-Token` header — a header, not a query parameter, so the secret does
    not end up in access logs.
    """
    expected = settings.CRON_TOKEN
    if not expected:
        raise Http404  # Endpoint is off unless a token is configured.

    provided = request.headers.get('X-Cron-Token', '')
    if not hmac.compare_digest(provided, expected):
        logger.warning('Rejected reconcile call with a bad token')
        return JsonResponse({'detail': 'forbidden'}, status=403)

    now = timezone.now()
    pending = Order.objects.filter(
        status=Order.Status.PENDING,
        created_at__lte=now - timezone.timedelta(minutes=2),
        created_at__gte=now - timezone.timedelta(hours=72),
    )

    settled = 0
    for order in pending:
        if services.refresh_from_bila(order).is_settled:
            settled += 1

    logger.info('Reconcile run: %s checked, %s settled', len(pending), settled)
    return JsonResponse({'checked': len(pending), 'settled': settled})
