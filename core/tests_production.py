"""Guards for the things that only bite in production."""
import tempfile
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from core.validators import validate_image_upload


def make_image(fmt='JPEG', size=(40, 40)):
    buffer = BytesIO()
    Image.new('RGB', size, (120, 90, 40)).save(buffer, format=fmt)
    buffer.seek(0)
    return buffer.getvalue()


class PasswordResetTests(TestCase):
    """A locked-out customer must have a self-service route back in."""

    def setUp(self):
        self.user = User.objects.create_user('ada', 'ada@example.com', 'old-password')

    def test_full_reset_flow_lets_the_user_log_in_again(self):
        response = self.client.post(reverse('core:password_reset'), {'email': 'ada@example.com'})
        self.assertRedirects(response, reverse('core:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)

        # Follow the link exactly as a customer would.
        link = [word for word in mail.outbox[0].body.split() if '/reset/' in word][0]
        path = link.split('testserver')[-1]
        response = self.client.get(path, follow=True)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(response.request['PATH_INFO'], {
            'new_password1': 'a-much-better-password-42',
            'new_password2': 'a-much-better-password-42',
        })
        self.assertRedirects(response, reverse('core:password_reset_complete'))
        self.assertTrue(self.client.login(username='ada', password='a-much-better-password-42'))

    def test_unknown_address_does_not_leak_whether_an_account_exists(self):
        response = self.client.post(reverse('core:password_reset'), {'email': 'nobody@example.com'})
        self.assertRedirects(response, reverse('core:password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_login_page_offers_the_reset_route(self):
        self.assertContains(self.client.get(reverse('core:login')), reverse('core:password_reset'))


@override_settings(MAX_UPLOAD_BYTES=1024)
class UploadValidationTests(TestCase):
    def test_oversized_upload_is_rejected_with_a_useful_message(self):
        big = SimpleUploadedFile('big.jpg', b'x' * 5000, content_type='image/jpeg')
        with self.assertRaises(ValidationError) as caught:
            validate_image_upload(big)
        self.assertIn('under', str(caught.exception))

    @override_settings(MAX_UPLOAD_BYTES=8 * 1024 * 1024)
    def test_normal_photo_is_accepted(self):
        ok = SimpleUploadedFile('ok.jpg', make_image(), content_type='image/jpeg')
        validate_image_upload(ok)  # must not raise

    @override_settings(MAX_UPLOAD_BYTES=8 * 1024 * 1024)
    def test_format_is_checked_from_the_file_not_the_filename(self):
        """A renamed file must not slip through on its extension alone."""
        class Fake:
            size = 100
            image = type('img', (), {'format': 'GIF'})()

        with self.assertRaises(ValidationError) as caught:
            validate_image_upload(Fake())
        self.assertIn('GIF', str(caught.exception))


class ErrorPageTests(TestCase):
    def test_404_uses_the_site_design(self):
        response = self.client.get('/no-such-page/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "This page isn't here.", status_code=404)

    def test_500_template_is_standalone(self):
        """It renders when the site is broken, so it must not extend base.html."""
        from django.template.loader import get_template
        source = get_template('500.html').template.source
        self.assertNotIn('{% extends', source)
        self.assertNotIn('{% url', source)


class StaticFilesTests(TestCase):
    def test_static_root_is_configured(self):
        """Without STATIC_ROOT, collectstatic fails and the admin loses its CSS."""
        from django.conf import settings
        self.assertTrue(settings.STATIC_ROOT)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), MAX_UPLOAD_BYTES=20*1024*1024)
class ImagePipelineTests(TestCase):
    """A raw phone photo must never reach a customer's browser."""

    def setUp(self):
        from item.models import Category, Item
        self.owner = User.objects.create_user('seller', password='x')
        self.category = Category.objects.create(name='Rings')
        self.Item = Item

    def upload(self, pixels=(3000, 2000), fmt='JPEG'):
        return SimpleUploadedFile(f'photo.{fmt.lower()}', make_image(fmt, pixels),
                                  content_type=f'image/{fmt.lower()}')

    def make(self):
        item = self.Item(category=self.category, name='Gold Band',
                         price=Decimal('100.00'), created_by=self.owner)
        item.image = self.upload()
        item.save()
        return item

    def test_upload_is_resized_and_a_thumbnail_generated(self):
        item = self.make()
        self.assertTrue(item.thumbnail)

        from PIL import Image as PILImage
        with PILImage.open(item.image) as full:
            self.assertLessEqual(max(full.size), 1600)
        with PILImage.open(item.thumbnail) as thumb:
            self.assertLessEqual(max(thumb.size), 700)

    def test_thumbnail_is_much_smaller_than_the_full_image(self):
        item = self.make()
        self.assertLess(item.thumbnail.size, item.image.size / 2)

    def test_output_is_webp_whatever_went_in(self):
        item = self.make()
        self.assertTrue(item.image.name.endswith('.webp'))
        self.assertTrue(item.thumbnail.name.endswith('.webp'))

    def test_card_image_prefers_the_thumbnail(self):
        item = self.make()
        self.assertEqual(item.card_image, item.thumbnail)

    def test_card_image_falls_back_when_there_is_no_thumbnail(self):
        item = self.Item.objects.create(category=self.category, name='No Photo',
                                        price=Decimal('10.00'), created_by=self.owner)
        self.assertFalse(item.card_image)

    def test_editing_an_item_does_not_re_encode_the_image(self):
        """Re-saving must not degrade the photo a little more each time."""
        item = self.make()
        original_name, original_size = item.image.name, item.image.size

        item.price = Decimal('200.00')
        item.save()
        item.refresh_from_db()

        self.assertEqual(item.image.name, original_name)
        self.assertEqual(item.image.size, original_size)

    def test_exif_orientation_is_applied_before_it_is_stripped(self):
        """Otherwise portrait phone photos would display sideways."""
        from PIL import Image as PILImage
        buffer = BytesIO()
        img = PILImage.new('RGB', (400, 200), (10, 20, 30))
        exif = img.getexif()
        exif[274] = 6  # "rotate 90 CW"
        img.save(buffer, format='JPEG', exif=exif)
        buffer.seek(0)

        item = self.Item(category=self.category, name='Rotated',
                         price=Decimal('10.00'), created_by=self.owner)
        item.image = SimpleUploadedFile('r.jpg', buffer.getvalue(), content_type='image/jpeg')
        item.save()

        with PILImage.open(item.image) as out:
            self.assertGreater(out.height, out.width)   # now genuinely portrait
            self.assertIsNone(out.getexif().get(274))   # and the tag is gone


@override_settings(RATELIMIT_ENABLE=True)
class RateLimitTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()   # LocMemCache persists between tests

    def test_login_is_throttled_by_username(self):
        User.objects.create_user('ada', password='right-password')
        url = reverse('core:login')
        for _ in range(5):
            self.client.post(url, {'username': 'ada', 'password': 'wrong'})

        response = self.client.post(url, {'username': 'ada', 'password': 'wrong'})
        self.assertEqual(response.status_code, 429)

    def test_signup_is_throttled(self):
        url = reverse('core:signup')
        for i in range(3):
            self.client.post(url, {'username': f'u{i}', 'email': f'u{i}@e.com',
                                   'password1': 'sw9fj2mfk3', 'password2': 'sw9fj2mfk3'})
        response = self.client.post(url, {'username': 'u9', 'email': 'u9@e.com',
                                          'password1': 'sw9fj2mfk3', 'password2': 'sw9fj2mfk3'})
        self.assertEqual(response.status_code, 429)

    def test_the_429_page_explains_itself(self):
        User.objects.create_user('ada', password='x')
        url = reverse('core:login')
        for _ in range(6):
            response = self.client.post(url, {'username': 'ada', 'password': 'wrong'})
        self.assertContains(response, 'One moment.', status_code=429)

    def test_ajax_gets_json_not_an_html_page(self):
        User.objects.create_user('ada', password='x')
        url = reverse('core:login')
        for _ in range(6):
            response = self.client.post(url, {'username': 'ada', 'password': 'wrong'},
                                        headers={'x-requested-with': 'XMLHttpRequest'})
        self.assertEqual(response.status_code, 429)
        self.assertIn('detail', response.json())

    @override_settings(RATELIMIT_ENABLE=False)
    def test_limits_are_off_during_tests_by_default(self):
        User.objects.create_user('ada', password='x')
        for _ in range(8):
            response = self.client.post(reverse('core:login'),
                                        {'username': 'ada', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)


class LegalAndDiscoveryTests(TestCase):
    def test_legal_pages_render(self):
        for name in ('terms', 'privacy', 'returns'):
            response = self.client.get(reverse(f'core:{name}'))
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, 'Last updated')

    def test_legal_pages_are_linked_from_every_page(self):
        body = self.client.get(reverse('core:index')).content.decode()
        for name in ('terms', 'privacy', 'returns'):
            self.assertIn(reverse(f'core:{name}'), body)

    def test_privacy_names_the_third_parties_that_receive_data(self):
        response = self.client.get(reverse('core:privacy'))
        self.assertContains(response, 'Bila')
        self.assertContains(response, 'Resend')

    def test_robots_blocks_private_areas(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response['Content-Type'], 'text/plain')
        for path in ('/admin/', '/cart/', '/orders/', '/dashboard/'):
            self.assertContains(response, f'Disallow: {path}')

    def test_favicon_is_referenced(self):
        self.assertContains(self.client.get(reverse('core:index')), 'favicon.svg')
