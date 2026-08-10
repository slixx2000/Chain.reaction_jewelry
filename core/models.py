from django.db import models


class SiteContent(models.Model):
    """Editable bits of the storefront that are not products.

    Deliberately a single row — `SiteContent.load()` creates it on first use, so
    templates never have to cope with it being missing.
    """

    hero_image = models.ImageField(
        upload_to='site/', blank=True,
        help_text='Landing page banner. Landscape, at least 1600px wide. '
                  'Leave empty to show a placeholder instead.',
    )
    hero_image_alt = models.CharField(
        max_length=200, blank=True,
        help_text='Describes the photo for screen readers and when it fails to load.',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site content'
        verbose_name_plural = 'Site content'

    def __str__(self):
        return 'Site content'

    def save(self, *args, **kwargs):
        self.pk = 1  # There is only ever one row.
        # create() would pass force_insert=True and collide with the existing
        # row; drop it so a second save updates rather than raising.
        kwargs.pop('force_insert', None)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # Deleting the only row would break the landing page.

    @classmethod
    def load(cls):
        content, _ = cls.objects.get_or_create(pk=1)
        return content

    @property
    def hero_alt_text(self):
        return self.hero_image_alt or 'Chain Reaction jewelry'
