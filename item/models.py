from django.contrib.auth.models import User
from django.db import models

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
    image = models.ImageField(upload_to='item_images/', blank=True, null=True) 
    badge = models.CharField(
        max_length=20, choices=Badge.choices, blank=True,
        help_text='Optional label shown on the corner of the card. Sold pieces never show one.',
    )
    is_sold = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # Optional on the form: the admin fills it in with whoever is editing.
    created_by = models.ForeignKey(User, related_name='items', on_delete=models.CASCADE,
                                   null=True, blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('item:detail', kwargs={'pk': self.pk})

    @property
    def badge_classes(self):
        """Tailwind colours for this item's badge, empty when it has none."""
        return self.BADGE_STYLES.get(self.badge, '')