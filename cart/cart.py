from item.models import Item


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get('cart_key')
        if not cart:
            cart = self.session['cart_key'] = {}
        self.cart = cart

    def add(self, item, quantity=1, override_quantity=False):
        item_id = str(item.id)
        if item_id not in self.cart:
            self.cart[item_id] = {'quantity': 0}

        if override_quantity:
            self.cart[item_id]['quantity'] = quantity
        else:
            self.cart[item_id]['quantity'] += quantity

        self.save()

    def save(self):
        self.session.modified = True

    def remove(self, item):
        item_id = str(item.id)
        if item_id in self.cart:
            del self.cart[item_id]
            self.save()

    def update(self, item, quantity):
        item_id = str(item.id)
        if quantity <= 0:
            self.remove(item)
            return

        if item_id in self.cart:
            self.cart[item_id]['quantity'] = quantity
            self.save()

    def __iter__(self):
        item_ids = self.cart.keys()
        items = Item.objects.filter(id__in=item_ids)

        cart = self.cart.copy()
        for item in items:
            cart[str(item.id)]['item'] = item

        for cart_item in cart.values():
            cart_item['total_price'] = cart_item['item'].price * cart_item['quantity']
            yield cart_item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(item['item'].price * item['quantity'] for item in self)