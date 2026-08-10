"""Settle orders whose webhook never arrived.

A customer can approve the PIN and immediately close the tab. If Bila's webhook
is also missed — a redeploy, a sleeping free-tier instance, a network blip —
nothing else ever asks Bila what happened and the order sits `pending` forever.
That means money received and not recorded, so this runs on a schedule.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from orders.models import Order
from orders import services


class Command(BaseCommand):
    help = 'Ask Bila about orders still pending, and settle the ones that resolved.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--older-than', type=int, default=2, metavar='MINUTES',
            help='Skip orders newer than this; the customer is probably still '
                 'entering their PIN (default: 2).',
        )
        parser.add_argument(
            '--max-age', type=int, default=72, metavar='HOURS',
            help='Stop chasing orders older than this (default: 72).',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would be checked without calling Bila.',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        pending = Order.objects.filter(
            status=Order.Status.PENDING,
            created_at__lte=now - timezone.timedelta(minutes=options['older_than']),
            created_at__gte=now - timezone.timedelta(hours=options['max_age']),
        ).order_by('created_at')

        if not pending:
            self.stdout.write('Nothing pending to reconcile.')
            return

        self.stdout.write(f'{pending.count()} pending order(s) to check.')
        settled = failed = unchanged = 0

        for order in pending:
            if options['dry_run']:
                self.stdout.write(f'  would check {order.reference}')
                continue

            refreshed = services.refresh_from_bila(order)
            if refreshed.status == Order.Status.PAID:
                settled += 1
                self.stdout.write(self.style.SUCCESS(
                    f'  {order.reference} → PAID (webhook was missed)'))
            elif refreshed.status == Order.Status.FAILED:
                failed += 1
                self.stdout.write(f'  {order.reference} → failed')
            else:
                unchanged += 1

        if not options['dry_run']:
            self.stdout.write(
                f'Done. {settled} newly paid, {failed} failed, {unchanged} still pending.')
