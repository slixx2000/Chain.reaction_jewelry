"""Order lifecycle. Everything that moves money or stock lives here, not in views."""
import logging

from django.db import transaction
from django.utils import timezone

from item.models import Item
from . import bila
from .emails import send_order_emails
from .models import Order, OrderItem

logger = logging.getLogger(__name__)


class OutOfStock(Exception):
    """A piece in the bag was sold before checkout completed."""

    def __init__(self, names):
        self.names = names
        super().__init__(', '.join(names))


@transaction.atomic
def create_order(cart, *, user, full_name, email, phone, operator, delivery_address):
    """Turn the session cart into a pending Order.

    Prices and availability are re-read from the database — the session is the
    customer's, so it is never trusted for money.
    """
    lines = list(cart)
    if not lines:
        raise ValueError('Your bag is empty.')

    item_ids = [line['item'].id for line in lines]
    items = Item.objects.select_for_update().filter(id__in=item_ids)
    by_id = {item.id: item for item in items}

    unavailable = [
        line['item'].name for line in lines
        if line['item'].id not in by_id or by_id[line['item'].id].is_sold
    ]
    if unavailable:
        raise OutOfStock(unavailable)

    order = Order(
        user=user if user and user.is_authenticated else None,
        full_name=full_name, email=email, phone=phone, operator=operator,
        delivery_address=delivery_address,
        total=sum(by_id[line['item'].id].price * line['quantity'] for line in lines),
    )
    order.save()

    OrderItem.objects.bulk_create([
        OrderItem(
            order=order, item=by_id[line['item'].id],
            name=by_id[line['item'].id].name,
            price=by_id[line['item'].id].price,
            quantity=line['quantity'],
        )
        for line in lines
    ])

    return order


def start_payment(order):
    """Ask Bila to prompt the customer. Returns the collection payload."""
    data = bila.initiate_collection(
        amount=order.total,
        reference=order.reference,
        phone=order.phone,
        operator=order.operator,
        narration=f'Chain Reaction order {order.reference}',
        customer_name=order.full_name,
    )

    order.bila_collection_id = str(data.get('id') or '')
    order.bila_status = str(data.get('status') or '')
    order.save(update_fields=['bila_collection_id', 'bila_status', 'updated_at'])

    apply_collection_status(order, data)
    return data


@transaction.atomic
def apply_collection_status(order, data):
    """Move the order to its settled state. Safe to call repeatedly.

    Bila delivers the same result by webhook and by polling, so this must be
    idempotent — the first terminal state wins and later calls are no-ops.
    """
    order = Order.objects.select_for_update().get(pk=order.pk)
    status = str(data.get('status') or '').lower()

    if order.is_settled:
        return order

    order.bila_status = status

    if status in bila.SUCCESS_STATUSES:
        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        _mark_items_sold(order)
        # Only once the payment is durably committed — and only once, because
        # the is_settled guard above makes this branch unreachable on replays.
        transaction.on_commit(lambda: send_order_emails(order))
        logger.info('Order %s paid', order.reference)
    elif status in bila.FAILURE_STATUSES:
        order.status = Order.Status.FAILED
        order.failure_reason = str(data.get('message') or 'Payment was not completed.')[:255]
        logger.info('Order %s failed: %s', order.reference, order.failure_reason)

    order.save()
    return order


def refresh_from_bila(order):
    """Poll Bila for the truth. Used by the status page and after a webhook ping."""
    if order.is_settled:
        return order
    try:
        data = bila.get_collection(order.reference)
    except bila.BilaError as exc:
        logger.warning('Could not refresh order %s: %s', order.reference, exc)
        return order
    return apply_collection_status(order, data)


def _mark_items_sold(order):
    """One-of-a-kind pieces leave the catalogue once they are paid for."""
    item_ids = [line.item_id for line in order.items.all() if line.item_id]
    if item_ids:
        Item.objects.filter(id__in=item_ids).update(is_sold=True)
