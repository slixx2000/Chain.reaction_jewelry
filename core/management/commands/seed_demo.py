"""Populate the shop with demo products so the UI can be reviewed.

Images are generated with Pillow rather than shipped as binaries — the repo
stays small and there is nothing to license.
"""
import hashlib
import io
import math
import random
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw

from item.models import Category, Item
from orders.models import Order

# (category, name, price, description)
PRODUCTS = [
    ('Necklaces', 'Copper Chain Reaction Pendant', '285.00',
     'Copper chain with a hammered pendant. The finish catches light unevenly, which is the point.'),
    ('Necklaces', 'Malachite Drop Necklace', '420.00',
     'Malachite set on a fine brass chain. The stone is cut to keep its natural banding, so every one differs.'),
    ('Necklaces', 'Twisted Wire Choker', '190.00',
     'Two strands of twisted copper sitting close to the neck, with an adjustable clasp.'),
    ('Bracelets', 'Hammered Cuff', '235.00',
     'A wide copper cuff with a hammered face, shaped to sit flat on the wrist.'),
    ('Bracelets', 'Beaded Kwacha Bracelet', '150.00',
     'Glass beads on waxed cord with a copper clasp. Sits comfortably under a sleeve.'),
    ('Bracelets', 'Braided Leather Wrap', '175.00',
     'Braided leather over a copper core, wrapping twice around the wrist.'),
    ('Earrings', 'Hoop Reaction Earrings', '165.00',
     'Lightweight copper hoops with a soft hammered finish. Barely there once they are on.'),
    ('Earrings', 'Teardrop Studs', '120.00',
     'Small polished teardrops on hypoallergenic posts. An everyday pair.'),
    ('Earrings', 'Long Chain Danglers', '210.00',
     'Fine chain drops that catch the light as you move. Under five grams a pair.'),
    ('Rings', 'Hammered Gold Band', '310.00',
     'A brass band with a hammered face, sealed to keep its shine. Stocked in a few sizes.'),
    ('Rings', 'Wire Wrap Ring', '95.00',
     'An open copper band that adjusts to fit.'),
    ('Rings', 'Stacking Trio', '260.00',
     'Three slim bands in copper, brass and oxidised copper, worn together or apart.'),
    ('Anklets', 'Beaded Anklet', '110.00',
     'Seed beads on a fine chain with an adjustable tail.'),
    ('Anklets', 'Copper Charm Anklet', '145.00',
     'Small hammered discs spaced along a delicate copper chain.'),
]

# Which demo pieces have already sold, so "Best Sellers" has something to rank.
SALES = {
    'Hoop Reaction Earrings': 6,
    'Hammered Cuff': 5,
    'Copper Chain Reaction Pendant': 4,
    'Beaded Kwacha Bracelet': 3,
    'Hammered Gold Band': 2,
}

PALETTES = [
    ((26, 28, 31), (210, 159, 34)),    # slate -> gold
    ((37, 38, 40), (166, 124, 26)),    # slate -> dark gold
    ((45, 30, 30), (184, 115, 84)),    # warm -> copper
    ((93, 0, 24), (210, 159, 34)),     # wine -> gold
    ((20, 30, 34), (140, 160, 150)),   # cool -> patina
]


def make_image(name, size=900):
    """A deterministic abstract product image — same name, same picture."""
    seed = int(hashlib.sha256(name.encode()).hexdigest(), 16)
    rng = random.Random(seed)
    top, bottom = PALETTES[seed % len(PALETTES)]

    image = Image.new('RGB', (size, size), top)
    draw = ImageDraw.Draw(image, 'RGBA')

    # Vertical gradient.
    for y in range(size):
        blend = y / size
        draw.line(
            [(0, y), (size, y)],
            fill=tuple(int(top[c] + (bottom[c] - top[c]) * blend) for c in range(3)),
        )

    # Concentric rings, offset like a piece resting off-centre.
    cx = size * rng.uniform(0.38, 0.62)
    cy = size * rng.uniform(0.38, 0.62)
    for ring in range(rng.randint(3, 6)):
        radius = size * (0.12 + ring * rng.uniform(0.05, 0.09))
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            outline=(255, 255, 255, rng.randint(18, 48)),
            width=rng.randint(2, 7),
        )

    # A few links suggesting a chain.
    for link in range(rng.randint(5, 9)):
        angle = rng.uniform(0, math.tau)
        distance = size * rng.uniform(0.18, 0.40)
        lx, ly = cx + math.cos(angle) * distance, cy + math.sin(angle) * distance
        r = size * rng.uniform(0.02, 0.05)
        draw.ellipse([lx - r, ly - r, lx + r, ly + r],
                     outline=(255, 255, 255, rng.randint(40, 90)), width=3)

    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=88)
    return ContentFile(buffer.getvalue(), name=f'{seed % 10**8}.jpg')


class Command(BaseCommand):
    help = 'Create demo categories, products and sales so the storefront can be reviewed.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Delete existing demo products and orders first.')

    @transaction.atomic
    def handle(self, *args, **options):
        owner = User.objects.filter(is_superuser=True).order_by('pk').first()
        if not owner:
            self.stderr.write(self.style.ERROR(
                'No superuser found. Run `manage.py createsuperuser` first.'))
            return

        names = [name for _, name, _, _ in PRODUCTS]

        if options['reset']:
            Order.objects.filter(reference__startswith='CR-DEMO').delete()
            deleted, _ = Item.objects.filter(name__in=names).delete()
            self.stdout.write(f'Removed {deleted} existing demo records.')

        created = 0
        items = {}
        for category_name, name, price, description in PRODUCTS:
            category, _ = Category.objects.get_or_create(name=category_name)
            item, was_created = Item.objects.get_or_create(
                name=name,
                defaults={
                    'category': category,
                    'price': Decimal(price),
                    'description': description,
                    'created_by': owner,
                },
            )
            if was_created:
                item.image.save(f'{name.lower().replace(" ", "-")}.jpg', make_image(name), save=True)
                created += 1
            items[name] = item

        self.stdout.write(self.style.SUCCESS(f'{created} new products created ({len(items)} total).'))
        self._seed_sales(items)

    def _seed_sales(self, items):
        """Paid orders, so the Best Sellers ranking has real data behind it."""
        if Order.objects.filter(reference__startswith='CR-DEMO').exists():
            self.stdout.write('Demo sales already present.')
            return

        made = 0
        for index, (name, quantity) in enumerate(SALES.items()):
            item = items.get(name)
            if not item:
                continue
            order = Order.objects.create(
                reference=f'CR-DEMO{index:04d}',
                full_name='Demo Customer',
                phone='260977000000',
                operator='airtel',
                delivery_address='Lusaka',
                total=item.price * quantity,
                status=Order.Status.PAID,
                paid_at=timezone.now(),
            )
            order.items.create(item=item, name=item.name, price=item.price, quantity=quantity)
            made += 1

        self.stdout.write(self.style.SUCCESS(f'{made} demo sales recorded.'))
