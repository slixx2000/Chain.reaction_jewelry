from django.contrib.auth.models import User
from django.db import models

from core import images
from core.validators import validate_image_upload

class Category(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ('name',)
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name
    

class Item(models.Model):
    class Badge(models.TextChoices):
        NEW = 'new', 'New'
        BEST_SELLER = 'best_seller', 'Best Seller'
        LIMITED = 'limited', 'Limited'

    # Tailwind classes per badge, kept next to the choices so the two cannot drift.
    BADGE_STYLES = {
        Badge.NEW: 'bg-antique text-obsidian',
        Badge.BEST_SELLER: 'bg-burgundy text-ivory',
        Badge.LIMITED: 'bg-ivory text-obsidian',
    }

    category = models.ForeignKey(Category, related_name='items', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='item_images/', blank=True, null=True,
                              validators=[validate_image_upload])
    # Generated from `image` on save; never set this by hand.
    thumbnail = models.ImageField(upload_to='item_images/thumbs/', blank=True, null=True,
                                  editable=False)
    badge = models.CharField(
        max_length=20, choices=Badge.choices, blank=True,
        help_text='Optional label shown on the corner of the card. Sold pieces never show one.',
    )
    is_sold = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # Optional on the form: the admin fills it in with whoever is editing.
    created_by = models.ForeignKey(User, related_name='items', on_delete=models.CASCADE,
                                   null=True, blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remember what was on disk so save() can tell whether a new file
        # arrived and avoid re-encoding an unchanged image on every edit.
        self._original_image = self.image.name if self.image else None

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        changed = self.image and self.image.name != self._original_image
        if changed:
            resized = images.full(self.image)
            if resized:
                self.image.save(resized.name, resized, save=False)
                thumb = images.thumbnail(self.image)
                if thumb:
                    self.thumbnail.save(thumb.name, thumb, save=False)
        elif not self.image:
            self.thumbnail = None

        super().save(*args, **kwargs)
        self._original_image = self.image.name if self.image else None

    @property
    def card_image(self):
        """Small image for grids, falling back to the full one."""
        return self.thumbnail or self.image

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('item:detail', kwargs={'pk': self.pk})

    @property
    def badge_classes(self):
        """Tailwind colours for this item's badge, empty when it has none."""
        return self.BADGE_STYLES.get(self.badge, '')