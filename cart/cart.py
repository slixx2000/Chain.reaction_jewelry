from item.models import Item

MAX_QUANTITY = 99


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
            new_quantity = quantity
        else:
            new_quantity = self.cart[item_id]['quantity'] + quantity

        self.cart[item_id]['quantity'] = max(1, min(new_quantity, MAX_QUANTITY))

        self.save()

    def save(self):
        self.session.modified = True

    def remove(self, item):
        item_id = str(item.id)
        if item_id in self.cart:
            del self.cart[item_id]
            self.save()

    def clear(self):
        self.cart = self.session['cart_key'] = {}
        self.save()

    def update(self, item, quantity):
        item_id = str(item.id)
        if quantity <= 0:
            self.remove(item)
            return

        if item_id in self.cart:
            self.cart[item_id]['quantity'] = min(quantity, MAX_QUANTITY)
            self.save()

    def __iter__(self):
        items = Item.objects.filter(id__in=self.cart.keys())
        found = {str(item.id): item for item in items}

        # Drop ids whose item no longer exists, otherwise iteration KeyErrors.
        stale = [item_id for item_id in self.cart if item_id not in found]
        if stale:
            for item_id in stale:
                del self.cart[item_id]
            self.save()

        for item_id, item in found.items():
            cart_item = dict(self.cart[item_id])
            cart_item['item'] = item
            cart_item['total_price'] = item.price * cart_item['quantity']
            yield cart_item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(item['total_price'] for item in self)
