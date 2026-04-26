from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.urls import reverse
from .cart import Cart
from item.models import Item

# Create your views here.


def cart_summary(request):
    cart = Cart(request)
    return render(request, 'cart/cart_summary.html', {'cart_items': cart})


def add_to_cart(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(Item, id=item_id)
        cart = Cart(request)
        cart.add(item)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'item_name': item.name,
                'item_price': f'{item.price:.2f}',
                'item_image': item.image.url if item.image else '',
                'cart_count': len(cart),
                'bag_url': reverse('cart:cart_summary'),
                'pay_url': f"{reverse('cart:cart_summary')}#checkout-button",
            })

    return redirect(request.META.get('HTTP_REFERER', 'cart:cart_summary'))

def remove_from_cart(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(Item, id=item_id)
        cart = Cart(request)
        cart.remove(item)
    return redirect('cart:cart_summary')


def update_cart_item(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(Item, id=item_id)
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 1
        cart = Cart(request)
        cart.update(item, quantity)
    return redirect('cart:cart_summary')