from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from item.models import Category, Item
from orders.models import Order


class LandingPageTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('seller', password='x')
        self.category = Category.objects.create(name='Rings')

    def make_item(self, name, sold=False):
        return Item.objects.create(
            category=self.category, name=name, price=Decimal('100.00'),
            created_by=self.owner, is_sold=sold,
        )

    def sell(self, item, quantity, status=Order.Status.PAID):
        order = Order.objects.create(
            full_name='Buyer', phone='260977123456', operator='airtel',
            delivery_address='Lusaka', total=item.price * quantity,
            status=status, paid_at=timezone.now(),
        )
        order.items.create(item=item, name=item.name, price=item.price, quantity=quantity)

    def test_best_sellers_rank_by_paid_quantity(self):
        popular, quiet = self.make_item('Popular'), self.make_item('Quiet')
        self.sell(popular, 5)
        self.sell(quiet, 1)

        best = self.client.get(reverse('core:index')).context['best_sellers']
        self.assertEqual([i.name for i in best], ['Popular', 'Quiet'])

    def test_unpaid_orders_do_not_count_towards_best_sellers(self):
        item = self.make_item('Pending Only')
        self.sell(item, 9, status=Order.Status.PENDING)

        self.assertEqual(self.client.get(reverse('core:index')).context['best_sellers'], [])

    def test_never_sold_items_are_excluded_rather_than_ranked_zero(self):
        self.make_item('Never Sold')
        self.assertEqual(self.client.get(reverse('core:index')).context['best_sellers'], [])

    def test_sold_out_pieces_are_not_advertised(self):
        gone = self.make_item('Gone', sold=True)
        self.sell(gone, 4)

        response = self.client.get(reverse('core:index'))
        self.assertEqual(response.context['best_sellers'], [])
        self.assertNotIn(gone, response.context['new_arrivals'])

    def test_category_counts_ignore_sold_pieces(self):
        self.make_item('Available')
        self.make_item('Gone', sold=True)

        category = self.client.get(reverse('core:index')).context['categories'].get()
        self.assertEqual(category.available_count, 1)

    def test_stock_count_covers_the_whole_catalogue_not_just_the_shown_slice(self):
        for n in range(12):                       # more than the 8 new_arrivals shown
            self.make_item(f'Piece {n}')
        self.make_item('Gone', sold=True)

        response = self.client.get(reverse('core:index'))
        self.assertEqual(len(response.context['new_arrivals']), 8)
        self.assertEqual(response.context['available_count'], 12)
        # Count and label live in separate tags, so check them separately.
        self.assertContains(response, '>12</p>')
        self.assertContains(response, 'pieces in stock')

    def test_stock_label_is_singular_for_one_piece(self):
        self.make_item('Only One')
        self.assertContains(self.client.get(reverse('core:index')), 'piece in stock')

    def test_empty_shop_still_renders(self):
        response = self.client.get(reverse('core:index'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['hero_item'])
