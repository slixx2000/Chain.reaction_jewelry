import uuid

from django.contrib.auth.models import User
from django.db import models

from item.models import Item


def new_reference():
    """Bila requires ^[a-zA-Z0-9._-]+$ — keep it to that alphabet."""
    return f'CR-{uuid.uuid4().hex[:12].upper()}'


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Awaiting payment'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    reference = models.CharField(max_length=40, unique=True, default=new_reference, editable=False)
    user = models.ForeignKey(User, related_name='orders', on_delete=models.SET_NULL, null=True, blank=True)

    full_name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, help_text='Mobile money number, e.g. 0977123456')
    operator = models.CharField(max_length=20)
    delivery_address = models.TextField()

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='ZMW')

    # Whatever Bila last told us, kept for support/reconciliation.
    bila_collection_id = models.CharField(max_length=64, blank=True)
    bila_status = models.CharField(max_length=32, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.reference} ({self.get_status_display()})'

    @property
    def is_settled(self):
        return self.status in {self.Status.PAID, self.Status.FAILED, self.Status.CANCELLED}


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    # Keep the row if the piece is later removed from the catalogue.
    item = models.ForeignKey(Item, related_name='order_items', on_delete=models.SET_NULL, null=True)

    # Snapshots — the catalogue price may change after the sale.
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.quantity} x {self.name}'

    @property
    def subtotal(self):
        return self.price * self.quantity
