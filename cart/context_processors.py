from .cart import Cart 

def cart_context_processor(request):
    cart = Cart(request)
    return {'cart': cart}