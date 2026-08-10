from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit
from .cart import Cart
from item.models import Item


def _back(request):
    """Referer redirect, but never off-site."""
    referer = request.META.get('HTTP_REFERER', '')
    if url_has_allowed_host_and_scheme(referer, {request.get_host()}, request.is_secure()):
        return redirect(referer)
    return redirect('cart:cart_summary')


def cart_summary(request):
    cart = Cart(request)
    return render(request, 'cart/cart_summary.html', {'cart_items': cart})


@ratelimit(key='ip', rate='60/m', method='POST', block=True)
@require_POST
def add_to_cart(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if item.is_sold:
        if is_ajax:
            return JsonResponse({'status': 'sold', 'message': f'"{item.name}" is already sold.'}, status=409)
        messages.error(request, f'"{item.name}" is already sold.')
        return _back(request)

    cart = Cart(request)
    cart.add(item)

    if is_ajax:
        return JsonResponse({
            'status': 'success',
            'item_name': item.name,
            'item_price': f'{item.price:.2f}',
            'item_image': item.image.url if item.image else '',
            'cart_count': len(cart),
            'bag_url': reverse('cart:cart_summary'),
            'pay_url': f"{reverse('cart:cart_summary')}#checkout-button",
        })

    messages.success(request, f'"{item.name}" added to your bag.')
    return _back(request)


@require_POST
def remove_from_cart(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    Cart(request).remove(item)
    return redirect('cart:cart_summary')


@require_POST
def update_cart_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1
    Cart(request).update(item, quantity)
    return redirect('cart:cart_summary')
