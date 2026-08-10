import tempfile
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.storefront import placements
from item.models import Category, Item
from orders.models import Order


class PlacementTests(TestCase):
    """`placements()` is what the admin reports, so it must match the landing page."""

    def setUp(self):
        self.owner = User.objects.create_user('seller', password='x')
        self.category = Category.objects.create(name='Rings')

    def make(self, name, sold=False):
        return Item.objects.create(
            category=self.category, name=name, price=Decimal('100.00'),
            created_by=self.owner, is_sold=sold,
        )

    def sell(self, item, quantity, status=Order.Status.PAID):
        order = Order.objects.create(
            full_name='B', phone='260977123456', operator='airtel',
            delivery_address='Lusaka', total=item.price * quantity,
            status=status, paid_at=timezone.now(),
        )
        order.items.create(item=item, name=item.name, price=item.price, quantity=quantity)

    def test_newest_available_piece_is_the_hero(self):
        self.make('Older')
        newest = self.make('Newest')
        self.assertEqual(placements()['hero_id'], newest.pk)

    def test_sold_pieces_appear_nowhere(self):
        gone = self.make('Gone', sold=True)
        self.sell(gone, 5)

        where = placements()
        self.assertNotEqual(where['hero_id'], gone.pk)
        self.assertNotIn(gone.pk, where['new_arrival_ids'])
        self.assertNotIn(gone.pk, where['best_seller_ids'])

    def test_best_sellers_need_a_paid_order(self):
        pending = self.make('Pending')
        paid = self.make('Paid')
        self.sell(pending, 9, status=Order.Status.PENDING)
        self.sell(paid, 1)

        self.assertEqual(placements()['best_seller_ids'], {paid.pk})

    def test_placements_agree_with_what_the_landing_page_renders(self):
        for n in range(3):
            self.make(f'Piece {n}')
        context = self.client.get(reverse('core:index')).context
        where = placements()

        self.assertEqual(where['hero_id'], context['hero_item'].pk)
        self.assertEqual(where['new_arrival_ids'], {i.pk for i in context['new_arrivals']})
        self.assertEqual(where['best_seller_ids'], {i.pk for i in context['best_sellers']})


# Smallest valid GIF — enough for an ImageField to render a URL.
PIXEL_GIF = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!'
    b'\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class BadgeDisplayTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('seller', password='x')
        self.category = Category.objects.create(name='Rings')

    def make(self, with_image=True, **kwargs):
        item = Item.objects.create(
            category=self.category, name='Gold Band', price=Decimal('150.00'),
            created_by=self.owner, **kwargs,
        )
        if with_image:
            item.image.save('pixel.gif', SimpleUploadedFile('pixel.gif', PIXEL_GIF), save=True)
        return item

    def test_badge_shows_on_the_browse_grid(self):
        self.make(badge=Item.Badge.LIMITED)
        response = self.client.get(reverse('item:items'))
        self.assertContains(response, 'Limited')

    def test_each_badge_has_its_own_colours(self):
        for value in (Item.Badge.NEW, Item.Badge.BEST_SELLER, Item.Badge.LIMITED):
            self.assertTrue(Item(badge=value).badge_classes, value)

    def test_no_badge_means_no_classes(self):
        self.assertEqual(Item(badge='').badge_classes, '')

    def test_sold_pieces_show_the_sold_stamp_instead_of_their_badge(self):
        item = self.make(badge=Item.Badge.LIMITED, is_sold=True)

        response = self.client.get(reverse('item:detail', args=[item.pk]))
        self.assertContains(response, 'Sold Out')
        self.assertNotContains(response, 'Limited')

    def test_sold_pieces_are_greyed_out(self):
        item = self.make(is_sold=True)
        response = self.client.get(reverse('item:detail', args=[item.pk]))
        self.assertContains(response, 'grayscale')
        self.assertContains(response, 'line-through')

    def test_available_pieces_are_not_greyed_out(self):
        item = self.make()
        response = self.client.get(reverse('item:detail', args=[item.pk]))
        self.assertNotContains(response, 'grayscale')


class BrowseGridTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('seller', password='x')
        self.category = Category.objects.create(name='Rings')

    def make(self, name, sold=False):
        return Item.objects.create(
            category=self.category, name=name, price=Decimal('100.00'),
            created_by=self.owner, is_sold=sold,
        )

    def names(self, response):
        return [item.name for item in response.context['items']]

    def test_sold_pieces_appear_but_sort_last(self):
        self.make('Sold A', sold=True)
        self.make('Available A')
        self.make('Sold B', sold=True)
        self.make('Available B')

        names = self.names(self.client.get(reverse('item:items')))
        self.assertEqual(set(names[:2]), {'Available A', 'Available B'})
        self.assertEqual(set(names[2:]), {'Sold A', 'Sold B'})

    def test_available_pieces_stay_newest_first(self):
        self.make('Older')
        self.make('Newer')
        self.assertEqual(self.names(self.client.get(reverse('item:items')))[:2], ['Newer', 'Older'])

    def test_counts_split_available_from_sold(self):
        self.make('One')
        self.make('Two')
        self.make('Gone', sold=True)

        response = self.client.get(reverse('item:items'))
        self.assertEqual(response.context['available_count'], 2)
        self.assertEqual(response.context['sold_count'], 1)

    def test_counts_respect_the_category_filter(self):
        other = Category.objects.create(name='Anklets')
        self.make('Ring', sold=True)
        Item.objects.create(category=other, name='Anklet', price=Decimal('10.00'),
                            created_by=self.owner)

        response = self.client.get(reverse('item:items'), {'category': other.pk})
        self.assertEqual((response.context['available_count'], response.context['sold_count']), (1, 0))

    def test_sold_piece_in_the_grid_cannot_be_added_to_a_bag(self):
        sold = self.make('Gone', sold=True)
        response = self.client.get(reverse('item:items'))

        self.assertContains(response, 'Sold Out')
        self.assertNotContains(response, reverse('cart:add_to_cart', args=[sold.pk]))


class ItemAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('boss', 'boss@example.com', 'x')
        self.category = Category.objects.create(name='Rings')
        self.item = Item.objects.create(
            category=self.category, name='Gold Band', price=Decimal('150.50'),
            created_by=self.admin,
        )
        self.client.force_login(self.admin)

    def test_changelist_renders_with_the_placement_column(self):
        response = self.client.get(reverse('admin:item_item_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Shows on')
        self.assertContains(response, 'Hero')       # only item, so it is the hero

    def test_changelist_renders_an_item_with_no_photo(self):
        Item.objects.create(category=self.category, name='No Photo',
                            price=Decimal('10.00'), created_by=self.admin)
        response = self.client.get(reverse('admin:item_item_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'no photo')

    def test_change_form_renders(self):
        response = self.client.get(
            reverse('admin:item_item_change', args=[self.item.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_category_changelist_counts_available_and_sold(self):
        Item.objects.create(category=self.category, name='Sold', price=Decimal('10.00'),
                            created_by=self.admin, is_sold=True)
        response = self.client.get(reverse('admin:item_category_changelist'))
        self.assertEqual(response.status_code, 200)
        category = response.context['cl'].result_list.get()
        self.assertEqual((category._available, category._sold), (1, 1))

    def test_mark_as_sold_action_pulls_the_piece_from_the_shop(self):
        self.client.post(reverse('admin:item_item_changelist'), {
            'action': 'mark_as_sold', '_selected_action': [self.item.pk],
        })
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_sold)

    def test_clear_badge_action(self):
        self.item.badge = Item.Badge.LIMITED
        self.item.save()

        self.client.post(reverse('admin:item_item_changelist'), {
            'action': 'clear_badge', '_selected_action': [self.item.pk],
        })
        self.item.refresh_from_db()
        self.assertEqual(self.item.badge, '')

    def test_creating_an_item_without_an_owner_assigns_the_editor(self):
        self.client.post(reverse('admin:item_item_add'), {
            'name': 'New Piece', 'category': self.category.pk,
            'description': '', 'price': '75.00',
        })
        self.assertEqual(Item.objects.get(name='New Piece').created_by, self.admin)
