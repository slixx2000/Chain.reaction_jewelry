"""Prove media storage really works, end to end, before trusting it with photos.

Writes a probe file, reads it back through Django, fetches it over the public
URL the way a customer's browser would, then deletes it. Each step is reported
separately, because they fail for different reasons: bad credentials, a bucket
that is not public, or a custom domain that is not wired up.
"""
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Verify the configured media storage can be written, read and served.'

    def handle(self, *args, **options):
        backend = settings.STORAGES['default']['BACKEND'].rsplit('.', 1)[-1]
        self.stdout.write(f'Backend: {backend}')

        if not settings.USE_R2:
            self.stdout.write(self.style.WARNING(
                'R2 is not configured, so this is the local disk. On a hosted box that '
                'means every redeploy deletes your product photos.'))
        else:
            self.stdout.write(f'Bucket : {settings.R2_BUCKET_NAME}')
            self.stdout.write(f'Public : {settings.R2_PUBLIC_URL or "(bucket endpoint)"}')
        self.stdout.write('')

        payload = b'chain-reaction storage probe'
        name = None

        try:
            name = default_storage.save('probe/storage-check.txt', ContentFile(payload))
            self.stdout.write(self.style.SUCCESS(f'  write  OK  -> {name}'))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'  write  FAILED: {exc}'))
            self.stderr.write('  Check the access key, secret and endpoint URL.')
            return

        try:
            with default_storage.open(name) as handle:
                assert handle.read() == payload
            self.stdout.write(self.style.SUCCESS('  read   OK'))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'  read   FAILED: {exc}'))

        url = default_storage.url(name)
        self.stdout.write(f'  url       {url}')

        if url.startswith('http'):
            try:
                import requests
                response = requests.get(url, timeout=20)
                if response.status_code == 200 and response.content == payload:
                    self.stdout.write(self.style.SUCCESS('  public OK  (a browser can fetch it)'))
                else:
                    self.stderr.write(self.style.ERROR(
                        f'  public FAILED: HTTP {response.status_code}'))
                    self.stderr.write('  The bucket or custom domain is not publicly readable. '
                                      'Product photos would 404 for customers.')
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f'  public FAILED: {exc}'))
        else:
            self.stdout.write('  public skipped (local file, not a URL)')

        try:
            default_storage.delete(name)
            self.stdout.write(self.style.SUCCESS('  delete OK'))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'  delete FAILED: {exc}'))
