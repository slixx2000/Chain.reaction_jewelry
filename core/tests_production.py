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
