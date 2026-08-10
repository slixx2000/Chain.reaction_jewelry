import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)


def _absolute(path):
    return f"{settings.SITE_URL.rstrip('/')}{path}"


def reply_to_address():
    """Where a customer's reply should actually arrive.

    DEFAULT_FROM_EMAIL is typically send-only (Resend does not host a mailbox),
    so replying to a receipt would bounce. Prefer an address someone reads.
    """
    if settings.REPLY_TO_EMAIL:
        return settings.REPLY_TO_EMAIL
    if settings.ORDER_NOTIFY_EMAILS:
        return settings.ORDER_NOTIFY_EMAILS[0]
    return settings.DEFAULT_FROM_EMAIL


def _context(order):
    return {
        'order': order,
        'lines': list(order.items.all()),
        'order_url': _absolute(reverse('orders:status', args=[order.reference])),
        'admin_url': _absolute(reverse('admin:orders_order_change', args=[order.pk])),
        'shop_email': reply_to_address(),
    }


def _send(*, subject, to, text_body, html_body=None, reply_to=None, what='email',
          connection=None):
    """Send and never raise. Payment already succeeded; mail is not allowed to undo that."""
    if not to:
        return False

    message = EmailMultiAlternatives(
        subject=subject, body=text_body, from_email=settings.DEFAULT_FROM_EMAIL,
        to=to, reply_to=reply_to or [reply_to_address()], connection=connection,
    )
    if html_body:
        message.attach_alternative(html_body, 'text/html')

    for attempt in (1, 2):
        try:
            message.send()
            break
        except Exception:
            if attempt == 1:
                logger.warning('Retrying %s to %s after a send failure', what, to)
                # A dead shared connection cannot be reused; let Django open one.
                message.connection = None
                continue
            logger.exception('Could not send %s to %s', what, to)
            return False

    logger.info('Sent %s to %s', what, to)
    return True


def send_order_emails(order):
    """Everything that goes out when an order is paid.

    Registered as a single on_commit callback, because Django runs those in
    sequence and stops at the first exception — one bad send must not silence
    the rest. `_send` already swallows delivery errors; this guards against a
    failure earlier than that, e.g. rendering a template.

    Both messages share one SMTP connection. Opening a second one is how the
    seller alert was lost in testing: the connection timed out even though the
    receipt had gone out seconds earlier.
    """
    try:
        connection = get_connection()
        connection.open()
    except Exception:
        # Fall back to a connection per message rather than sending nothing.
        logger.exception('Could not open a shared mail connection for order %s', order.reference)
        connection = None

    try:
        for name, send in (('receipt', send_receipt), ('seller notification', notify_seller)):
            try:
                send(order, connection=connection)
            except Exception:
                logger.exception('Sending the %s failed for order %s', name, order.reference)
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


def send_receipt(order, connection=None):
    """Email the customer their receipt."""
    if not order.email:
        return False

    context = _context(order)
    return _send(
        subject=f'Your Chain Reaction order {order.reference}',
        to=[order.email],
        text_body=render_to_string('orders/email/receipt.txt', context),
        html_body=render_to_string('orders/email/receipt.html', context),
        what=f'receipt for {order.reference}',
        connection=connection,
    )


def notify_seller(order, connection=None):
    """Tell the shop a paid order is waiting to be packed."""
    recipients = settings.ORDER_NOTIFY_EMAILS
    if not recipients:
        logger.warning('ORDER_NOTIFY_EMAIL is not set — nobody was told about order %s', order.reference)
        return False

    return _send(
        subject=f'New order {order.reference} — ZMW {order.total:.2f}',
        to=recipients,
        text_body=render_to_string('orders/email/seller_notification.txt', _context(order)),
        # So hitting reply goes to the customer, not back to the shop.
        reply_to=[order.email] if order.email else None,
        what=f'seller notification for {order.reference}',
        connection=connection,
    )
