"""What the landing page shows, in one place.

The admin reports these placements back to the shop owner, so this must stay
the single definition — two copies would drift and the admin would start lying
about where a piece appears.
"""
from django.db.models import Q, Sum

from item.models import Item

NEW_ARRIVAL_LIMIT = 8
BEST_SELLER_LIMIT = 4


def available_items():
    return Item.objects.filter(is_sold=False).select_related('category')


def new_arrivals(limit=NEW_ARRIVAL_LIMIT):
    """Newest pieces still for sale. The first one is the hero."""
    return list(available_items().order_by('-created_at')[:limit])


def best_sellers(limit=BEST_SELLER_LIMIT):
    """Ranked by quantity across paid orders only."""
    return list(
        available_items()
        .annotate(sold_count=Sum('order_items__quantity',
                                 filter=Q(order_items__order__status='paid')))
        .filter(sold_count__gt=0)
        .order_by('-sold_count')[:limit]
    )


def placements():
    """Where each piece currently appears on the landing page, by id."""
    arrivals = new_arrivals()
    return {
        'hero_id': arrivals[0].pk if arrivals else None,
        'new_arrival_ids': {item.pk for item in arrivals},
        'best_seller_ids': {item.pk for item in best_sellers()},
    }
