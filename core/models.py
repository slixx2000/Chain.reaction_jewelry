from django.db import models

from . import images
from .validators import validate_image_upload


class SiteContent(models.Model):
    """Editable bits of the storefront that are not products.

    Deliberately a single row — `SiteContent.load()` creates it on first use, so
    templates never have to cope with it being missing.
    """

    hero_image = models.ImageField(
        upload_to='site/', blank=True, validators=[validate_image_upload],
        help_text='Landing page banner. Landscape, at least 1600px wide. '
                  'Leave empty to show a placeholder instead.',
    )
    hero_image_alt = models.CharField(
        max_length=200, blank=True,
        help_text='Describes the photo for screen readers and when it fails to load.',
    )
    studio_image = models.ImageField(
        upload_to='site/', blank=True, validators=[validate_image_upload],
        help_text='The tall image beside “Why us” on the home page. Portrait, '
                  'around 1200 × 1600 — pieces laid out on stone or linen. '
                  'Leave empty to show a placeholder instead.',
    )
    studio_image_alt = models.CharField(
        max_length=200, blank=True,
        help_text='Describes the photo for screen readers and when it fails to load.',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site content'
        verbose_name_plural = 'Site content'

    def __str__(self):
        return 'Site content'

    IMAGE_FIELDS = ('hero_image', 'studio_image')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._remember_originals()

    def _remember_originals(self):
        for name in self.IMAGE_FIELDS:
            field = getattr(self, name)
            setattr(self, f'_original_{name}', field.name if field else None)

    def save(self, *args, **kwargs):
        for name in self.IMAGE_FIELDS:
            field = getattr(self, name)
            if field and field.name != getattr(self, f'_original_{name}'):
                # Full-bleed imagery, so more headroom than a product shot.
                resized = images.process(field, max_side=2200)
                if resized:
                    field.save(resized.name, resized, save=False)

        self.pk = 1  # There is only ever one row.
        # create() would pass force_insert=True and collide with the existing
        # row; drop it so a second save updates rather than raising.
        kwargs.pop('force_insert', None)
        super().save(*args, **kwargs)
        self._remember_originals()

    def delete(self, *args, **kwargs):
        pass  # Deleting the only row would break the landing page.

    @classmethod
    def load(cls):
        content, _ = cls.objects.get_or_create(pk=1)
        return content

    @property
    def hero_alt_text(self):
        return self.hero_image_alt or 'Chain Reaction jewelry'

    @property
    def studio_alt_text(self):
        return self.studio_image_alt or 'Jewelry laid out in the studio'
