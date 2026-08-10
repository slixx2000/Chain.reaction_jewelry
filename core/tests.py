import tempfile
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import SiteContent
from item.models import Category, Item
from orders.models import Order

# Smallest valid GIF — enough for an ImageField to render a URL.
PIXEL_GIF = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!'
    b'\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
)


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
        self.assertContains(response, '12 pieces in stock')

    def test_stock_label_is_singular_for_one_piece(self):
        self.make_item('Only One')
        self.assertContains(self.client.get(reverse('core:index')), 'piece in stock')

    def test_empty_shop_still_renders(self):
        response = self.client.get(reverse('core:index'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['hero_item'])


class HonestCopyTests(TestCase):
    """The jewelry is sourced and resold, not made here. No page may claim otherwise."""

    FORBIDDEN = ('handmade', 'hand-made', 'handcrafted', 'hand-crafted',
                 'made by hand', 'crafted in', 'artisan', 'commission')

    def setUp(self):
        owner = User.objects.create_user('seller', password='x')
        category = Category.objects.create(name='Rings')
        self.item = Item.objects.create(
            category=category, name='Gold Band', price=Decimal('100.00'),
            created_by=owner,
        )

    def assert_no_making_claims(self, url):
        body = self.client.get(url).content.decode().lower()
        for phrase in self.FORBIDDEN:
            self.assertNotIn(phrase, body, f'"{phrase}" appears on {url}')

    def test_landing_page_makes_no_making_claims(self):
        self.assert_no_making_claims(reverse('core:index'))

    def test_browse_and_detail_make_no_making_claims(self):
        self.assert_no_making_claims(reverse('item:items'))
        self.assert_no_making_claims(reverse('item:detail', args=[self.item.pk]))

    def test_contact_page_makes_no_making_claims(self):
        self.assert_no_making_claims(reverse('core:contact'))

    def test_sold_detail_page_makes_no_making_claims(self):
        self.item.is_sold = True
        self.item.save()
        self.assert_no_making_claims(reverse('item:detail', args=[self.item.pk]))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class HeroBannerTests(TestCase):
    """The hero image is swapped from the admin, never from code."""

    def setUp(self):
        self.admin = User.objects.create_superuser('boss', 'boss@example.com', 'x')

    def test_placeholder_shows_until_a_banner_is_uploaded(self):
        response = self.client.get(reverse('core:index'))
        self.assertContains(response, 'Photo pending')
        self.assertContains(response, 'Hero campaign image')

    def test_uploaded_banner_replaces_the_placeholder(self):
        content = SiteContent.load()
        content.hero_image.save('hero.gif', SimpleUploadedFile('hero.gif', PIXEL_GIF), save=True)

        response = self.client.get(reverse('core:index'))
        self.assertContains(response, content.hero_image.url)
        self.assertNotContains(response, 'Hero campaign image')

    def test_alt_text_is_used_when_given(self):
        content = SiteContent.load()
        content.hero_image_alt = 'Gold hoops worn at dusk'
        content.hero_image.save('hero.gif', SimpleUploadedFile('hero.gif', PIXEL_GIF), save=True)

        self.assertContains(self.client.get(reverse('core:index')), 'Gold hoops worn at dusk')

    def test_alt_text_falls_back_rather_than_being_empty(self):
        self.assertEqual(SiteContent(hero_image_alt='').hero_alt_text, 'Chain Reaction jewelry')

    def test_only_one_row_can_ever_exist(self):
        SiteContent.load()
        SiteContent.objects.create()
        SiteContent.objects.create()
        self.assertEqual(SiteContent.objects.count(), 1)

    def test_the_row_cannot_be_deleted_out_from_under_the_landing_page(self):
        SiteContent.load().delete()
        self.assertEqual(SiteContent.objects.count(), 1)

    def test_admin_list_jumps_straight_to_the_single_record(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:core_sitecontent_changelist'))
        self.assertRedirects(
            response, reverse('admin:core_sitecontent_change', args=[1])
        )

    def test_admin_edit_page_renders(self):
        self.client.force_login(self.admin)
        SiteContent.load()
        response = self.client.get(reverse('admin:core_sitecontent_change', args=[1]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Landing page banner')
