from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta

from orders.models import Order


class Command(BaseCommand):
    help = (
        "Cancel pending orders older than a given number of days and optionally purge cancelled orders."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--pending-days',
            type=int,
            default=7,
            help='Cancel orders in status "pending" older than this many days (default: 7)'
        )
        parser.add_argument(
            '--purge-cancelled-days',
            type=int,
            default=30,
            help='Delete orders that are already cancelled and older than this many days (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without modifying the database.'
        )

    def handle(self, *args, **options):
        pending_days = options['pending_days']
        purge_days = options['purge_cancelled_days']
        dry_run = options['dry_run']

        now = timezone.now()
        pending_cutoff = now - timedelta(days=pending_days)
        purge_cutoff = now - timedelta(days=purge_days)

        pending_qs = Order.objects.filter(status='pending', created_at__lt=pending_cutoff)
        cancelled_qs = Order.objects.filter(status='cancelled', updated_at__lt=purge_cutoff)

        self.stdout.write(f"Pending orders older than {pending_days} days: {pending_qs.count()}")
        self.stdout.write(f"Cancelled orders older than {purge_days} days: {cancelled_qs.count()}")

        if dry_run:
            self.stdout.write("Dry run — no changes will be made.")
            return

        # Cancel pending orders
        cancelled_count = 0
        for order in pending_qs.iterator():
            order.status = 'cancelled'
            order.notes = (order.notes or '') + f"\nAuto-cancelled by cleanup command (older than {pending_days} days)."
            order.save(update_fields=['status', 'notes', 'updated_at'])
            cancelled_count += 1

        # Purge old cancelled orders (delete)
        purged_count, _ = cancelled_qs.delete()

        self.stdout.write(self.style.SUCCESS(f"Cancelled {cancelled_count} pending orders."))
        self.stdout.write(self.style.SUCCESS(f"Purged {purged_count} order-related objects (including orders)"))
