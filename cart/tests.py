from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from item.models import Category, Item


class CartTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('seller', password='x')
        self.category = Category.objects.create(name='Rings')
        self.item = Item.objects.create(
            category=self.category, name='Gold Band', price=Decimal('150.50'),
            created_by=self.user,
        )

    def add(self, item=None):
        return self.client.post(reverse('cart:add_to_cart', args=[(item or self.item).id]))

    def test_add_and_total_uses_exact_decimals(self):
        self.add()
        self.add()
        response = self.client.get(reverse('cart:cart_summary'))
        self.assertContains(response, 'ZMW 301.00')

    def test_sold_item_cannot_be_added(self):
        self.item.is_sold = True
        self.item.save()
        self.add()
        self.assertEqual(self.client.session.get('cart_key', {}), {})

    def test_deleted_item_does_not_break_the_bag(self):
        self.add()
        self.item.delete()
        response = self.client.get(reverse('cart:cart_summary'))
        self.assertEqual(response.status_code, 200)

    def test_quantity_is_clamped(self):
        self.add()
        self.client.post(reverse('cart:update_cart_item', args=[self.item.id]), {'quantity': 10 ** 6})
        session_cart = self.client.session['cart_key']
        self.assertEqual(session_cart[str(self.item.id)]['quantity'], 99)

    def test_add_to_cart_rejects_get(self):
        self.assertEqual(self.client.get(reverse('cart:add_to_cart', args=[self.item.id])).status_code, 405)

    def test_referer_redirect_stays_on_site(self):
        response = self.add_with_referer('https://evil.example/steal')
        self.assertEqual(response.url, reverse('cart:cart_summary'))

    def add_with_referer(self, referer):
        return self.client.post(
            reverse('cart:add_to_cart', args=[self.item.id]), HTTP_REFERER=referer,
        )


class ItemDeleteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('seller', password='x')
        self.item = Item.objects.create(
            category=Category.objects.create(name='Rings'), name='Gold Band',
            price=Decimal('10.00'), created_by=self.user,
        )
        self.client.force_login(self.user)

    def test_get_does_not_delete(self):
        self.client.get(reverse('item:delete', args=[self.item.id]))
        self.assertTrue(Item.objects.filter(pk=self.item.pk).exists())

    def test_post_deletes(self):
        self.client.post(reverse('item:delete', args=[self.item.id]))
        self.assertFalse(Item.objects.filter(pk=self.item.pk).exists())

    def test_other_user_cannot_delete(self):
        self.client.force_login(User.objects.create_user('thief', password='x'))
        self.assertEqual(
            self.client.post(reverse('item:delete', args=[self.item.id])).status_code, 404
        )
