import hashlib
import hmac
import json
import time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from item.models import Category, Item
from orders import bila, services
from orders.models import Order

SECRET = 'whsec_test'


class PhoneTests(TestCase):
    def test_normalises_local_and_international_forms(self):
        for raw in ['0977123456', '+260 977 123 456', '260977123456', '977123456']:
            self.assertEqual(bila.normalise_phone(raw), '260977123456', raw)

    def test_rejects_wrong_length(self):
        with self.assertRaises(ValueError):
            bila.normalise_phone('12345')

    def test_detects_operator(self):
        self.assertEqual(bila.detect_operator('260977123456'), 'airtel')
        self.assertEqual(bila.detect_operator('260967123456'), 'mtn')
        self.assertEqual(bila.detect_operator('260957123456'), 'zamtel')

    def test_unknown_prefix_is_rejected(self):
        with self.assertRaises(ValueError):
            bila.detect_operator('260217123456')


@override_settings(BILA_WEBHOOK_SECRET=SECRET)
class WebhookSignatureTests(TestCase):
    def sign(self, body, timestamp=None, secret=SECRET):
        timestamp = timestamp or int(time.time())
        digest = hmac.new(secret.encode(), f'{timestamp}.'.encode() + body, hashlib.sha256).hexdigest()
        return str(timestamp), f'sha256={digest}'

    def test_valid_signature_passes(self):
        body = b'{"event":"collection.completed"}'
        timestamp, signature = self.sign(body)
        self.assertTrue(bila.verify_webhook(body, timestamp, signature))

    def test_tampered_body_fails(self):
        timestamp, signature = self.sign(b'{"amount":1}')
        self.assertFalse(bila.verify_webhook(b'{"amount":99999}', timestamp, signature))

    def test_wrong_secret_fails(self):
        body = b'{}'
        timestamp, signature = self.sign(body, secret='whsec_other')
        self.assertFalse(bila.verify_webhook(body, timestamp, signature))

    def test_replayed_old_timestamp_fails(self):
        body = b'{}'
        timestamp, signature = self.sign(body, timestamp=int(time.time()) - 3600)
        self.assertFalse(bila.verify_webhook(body, timestamp, signature))

    def test_missing_headers_fail(self):
        self.assertFalse(bila.verify_webhook(b'{}', None, None))


class OrderFlowTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user('seller', password='x')
        category = Category.objects.create(name='Rings')
        self.item = Item.objects.create(
            category=category, name='Gold Band', price=Decimal('150.50'), created_by=self.seller,
        )
        self.client.post(reverse('cart:add_to_cart', args=[self.item.id]))

    def checkout(self, **overrides):
        data = {
            'full_name': 'Ada Banda',
            'email': 'ada@example.com',
            'phone': '0977123456',
            'delivery_address': 'Plot 5, Lusaka',
        }
        data.update(overrides)
        return self.client.post(reverse('orders:checkout'), data)

    @patch('orders.services.bila.initiate_collection')
    def test_checkout_creates_pending_order_with_snapshot_prices(self, initiate):
        initiate.return_value = {'id': 'col_1', 'status': 'pending'}
        self.checkout()

        order = Order.objects.get()
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.total, Decimal('150.50'))
        self.assertEqual(order.phone, '260977123456')
        self.assertEqual(order.operator, 'airtel')

        line = order.items.get()
        self.assertEqual(line.price, Decimal('150.50'))

        # Price snapshot survives a later catalogue change.
        self.item.price = Decimal('999.00')
        self.item.save()
        line.refresh_from_db()
        self.assertEqual(line.price, Decimal('150.50'))

    @patch('orders.services.bila.initiate_collection')
    def test_total_is_recomputed_from_the_database(self, initiate):
        """A tampered session must not change what the customer is charged."""
        initiate.return_value = {'id': 'col_1', 'status': 'pending'}
        session = self.client.session
        session['cart_key'][str(self.item.id)]['quantity'] = 3
        session.save()

        self.checkout()
        self.assertEqual(Order.objects.get().total, Decimal('451.50'))
        self.assertEqual(initiate.call_args.kwargs['amount'], Decimal('451.50'))

    @patch('orders.services.bila.initiate_collection')
    def test_successful_payment_marks_item_sold_and_clears_bag(self, initiate):
        initiate.return_value = {'id': 'col_1', 'status': 'successful'}
        self.checkout()

        order = Order.objects.get()
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertIsNotNone(order.paid_at)
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_sold)

        self.client.get(reverse('orders:status', args=[order.reference]))
        self.assertEqual(self.client.session.get('cart_key'), {})

    @patch('orders.services.bila.initiate_collection')
    def test_failed_payment_leaves_item_on_sale(self, initiate):
        initiate.return_value = {'id': 'col_1', 'status': 'failed', 'message': 'Insufficient funds'}
        self.checkout()

        order = Order.objects.get()
        self.assertEqual(order.status, Order.Status.FAILED)
        self.item.refresh_from_db()
        self.assertFalse(self.item.is_sold)

    @patch('orders.services.bila.initiate_collection')
    def test_provider_outage_does_not_leave_a_silent_pending_order(self, initiate):
        initiate.side_effect = bila.BilaError('connection refused')
        self.checkout()

        order = Order.objects.get()
        self.assertEqual(order.status, Order.Status.FAILED)
        self.item.refresh_from_db()
        self.assertFalse(self.item.is_sold)

    def test_checkout_blocks_an_already_sold_item(self):
        self.item.is_sold = True
        self.item.save()
        response = self.checkout()
        self.assertRedirects(response, reverse('cart:cart_summary'))
        self.assertFalse(Order.objects.exists())

    def test_bad_phone_number_is_rejected_before_an_order_exists(self):
        self.checkout(phone='12345')
        self.assertFalse(Order.objects.exists())

    @patch('orders.services.bila.initiate_collection')
    def test_another_visitor_cannot_read_the_order(self, initiate):
        initiate.return_value = {'id': 'col_1', 'status': 'pending'}
        self.checkout()
        order = Order.objects.get()

        stranger = self.client_class()
        self.assertEqual(
            stranger.get(reverse('orders:status', args=[order.reference])).status_code, 404
        )


class CheckoutMixin:
    """One paid-order checkout, with on_commit callbacks actually executed."""

    def setUp(self):
        seller = User.objects.create_user('seller', password='x')
        self.item = Item.objects.create(
            category=Category.objects.create(name='Rings'), name='Gold Band',
            price=Decimal('150.50'), created_by=seller,
        )
        self.client.post(reverse('cart:add_to_cart', args=[self.item.id]))

    def checkout(self, status='successful', email='ada@example.com'):
        with patch('orders.services.bila.initiate_collection', return_value={'id': 'c1', 'status': status}):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(reverse('orders:checkout'), {
                    'full_name': 'Ada Banda', 'email': email,
                    'phone': '0977123456', 'delivery_address': 'Plot 5, Lusaka',
                })
        return Order.objects.get()

    def sent_to(self, address):
        return [m for m in mail.outbox if address in m.to]


@override_settings(ORDER_NOTIFY_EMAILS=[])
class ReceiptEmailTests(CheckoutMixin, TestCase):
    def test_receipt_is_sent_on_successful_payment(self):
        order = self.checkout()

        self.assertEqual(len(mail.outbox), 1)
        receipt = mail.outbox[0]
        self.assertEqual(receipt.to, ['ada@example.com'])
        self.assertIn(order.reference, receipt.subject)
        self.assertIn('Gold Band', receipt.body)
        self.assertIn('150.50', receipt.body)

    def test_receipt_has_a_html_alternative(self):
        self.checkout()
        html, mimetype = mail.outbox[0].alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        self.assertIn('Gold Band', html)

    @override_settings(SITE_URL='https://shop.example')
    def test_receipt_links_to_the_public_order_url(self):
        order = self.checkout()
        self.assertIn(f'https://shop.example/orders/{order.reference}/', mail.outbox[0].body)

    def test_no_receipt_when_payment_fails(self):
        self.checkout(status='failed')
        self.assertEqual(len(mail.outbox), 0)

    def test_no_receipt_and_no_crash_when_no_email_given(self):
        order = self.checkout(email='')
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(len(mail.outbox), 0)

    def test_a_broken_mail_server_does_not_break_the_paid_order(self):
        with patch('orders.emails.EmailMultiAlternatives.send', side_effect=OSError('smtp down')):
            order = self.checkout()

        self.assertEqual(order.status, Order.Status.PAID)
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_sold)


@override_settings(ORDER_NOTIFY_EMAILS=['shop@example.com'])
class SellerNotificationTests(CheckoutMixin, TestCase):
    def test_shop_is_alerted_with_what_to_pack_and_where(self):
        order = self.checkout()

        alert = self.sent_to('shop@example.com')[0]
        self.assertIn(order.reference, alert.subject)
        self.assertIn('150.50', alert.subject)
        self.assertIn('Gold Band', alert.body)
        self.assertIn('Plot 5, Lusaka', alert.body)
        self.assertIn('260977123456', alert.body)

    def test_reply_goes_to_the_customer(self):
        self.checkout()
        self.assertEqual(self.sent_to('shop@example.com')[0].reply_to, ['ada@example.com'])

    def test_customer_and_shop_both_get_exactly_one_email(self):
        self.checkout()
        self.assertEqual(len(self.sent_to('ada@example.com')), 1)
        self.assertEqual(len(self.sent_to('shop@example.com')), 1)

    def test_shop_is_alerted_even_when_the_customer_left_no_email(self):
        self.checkout(email='')
        self.assertEqual(len(self.sent_to('shop@example.com')), 1)
        self.assertIn('260977123456', self.sent_to('shop@example.com')[0].body)

    def test_a_failed_receipt_still_alerts_the_shop(self):
        # send_order_emails resolves each sender from module globals at call
        # time, so patching it here is what the dispatcher actually sees.
        with patch('orders.emails.send_receipt', side_effect=OSError('boom')):
            order = self.checkout()

        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(len(self.sent_to('shop@example.com')), 1)

    def test_no_alert_when_payment_fails(self):
        self.checkout(status='failed')
        self.assertEqual(mail.outbox, [])

    @override_settings(ORDER_NOTIFY_EMAILS=[])
    def test_unconfigured_recipient_does_not_break_the_order(self):
        order = self.checkout()
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(len(self.sent_to('ada@example.com')), 1)


@override_settings(BILA_WEBHOOK_SECRET=SECRET)
class WebhookViewTests(TestCase):
    def setUp(self):
        seller = User.objects.create_user('seller', password='x')
        self.item = Item.objects.create(
            category=Category.objects.create(name='Rings'), name='Gold Band',
            price=Decimal('100.00'), created_by=seller,
        )
        self.order = Order.objects.create(
            full_name='Ada', phone='260977123456', operator='airtel',
            delivery_address='Lusaka', total=Decimal('100.00'),
        )
        self.order.items.create(item=self.item, name=self.item.name, price=self.item.price)

    def post(self, payload, sign=True):
        body = json.dumps(payload).encode()
        timestamp = str(int(time.time()))
        digest = hmac.new(SECRET.encode(), f'{timestamp}.'.encode() + body, hashlib.sha256).hexdigest()
        return self.client.post(
            reverse('orders:bila_webhook'), data=body, content_type='application/json',
            headers={
                'x-bila-timestamp': timestamp,
                'x-bila-signature': f'sha256={digest}' if sign else 'sha256=deadbeef',
            },
        )

    @patch('orders.services.bila.get_collection')
    def test_unsigned_webhook_cannot_mark_an_order_paid(self, get_collection):
        get_collection.return_value = {'status': 'successful'}
        response = self.post({'data': {'reference': self.order.reference}}, sign=False)

        self.assertEqual(response.status_code, 401)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING)
        get_collection.assert_not_called()

    @patch('orders.services.bila.get_collection')
    def test_signed_webhook_settles_the_order_from_the_api_not_the_body(self, get_collection):
        get_collection.return_value = {'status': 'successful'}
        # The body claims failure; Bila's API is the source of truth.
        response = self.post({'event': 'collection.failed', 'data': {'reference': self.order.reference, 'status': 'failed'}})

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PAID)

    @patch('orders.services.bila.get_collection')
    def test_replayed_webhook_is_idempotent(self, get_collection):
        get_collection.return_value = {'status': 'successful'}
        self.post({'data': {'reference': self.order.reference}})
        first = Order.objects.get(pk=self.order.pk).paid_at

        get_collection.return_value = {'status': 'failed'}
        self.post({'data': {'reference': self.order.reference}})

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertEqual(self.order.paid_at, first)

    @patch('orders.services.bila.get_collection')
    def test_unknown_reference_is_acknowledged_without_side_effects(self, get_collection):
        response = self.post({'data': {'reference': 'CR-DOESNOTEXIST'}})
        self.assertEqual(response.status_code, 200)
        get_collection.assert_not_called()
