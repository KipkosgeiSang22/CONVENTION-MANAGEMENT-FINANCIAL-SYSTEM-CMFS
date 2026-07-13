"""
FILE: cmfs/cmfs_backend/conventions/management/commands/setup_schedules.py
ACTION: CREATE (Phase 11)

Registers every recurring Django Q2 Schedule the system relies on. Run
once after deploying (or after a fresh migrate), same as
create_super_admin / seed_data:

    python manage.py setup_schedules

Idempotent — uses get_or_create keyed on `func`, so re-running is safe
and won't create duplicate schedules.
"""

from django.core.management.base import BaseCommand
from django_q.models import Schedule


class Command(BaseCommand):
    help = 'Registers the recurring Django Q2 background jobs (cron schedules).'

    def handle(self, *args, **options):
        schedules = [
            {
                'func': 'conventions.tasks.auto_transition_convention_status',
                'name': 'Auto-transition convention status (daily)',
                'schedule_type': Schedule.DAILY,
            },
            {
                'func': 'conventions.tasks.check_annual_summary_trigger',
                'name': 'Check annual summary trigger (daily)',
                'schedule_type': Schedule.DAILY,
            },
            {
                'func': 'payments.tasks.reconcile_mpesa_payments',
                'name': 'Nightly M-Pesa reconciliation (daily)',
                'schedule_type': Schedule.DAILY,
            },
            {
                'func': 'payments.tasks.retry_failed_stk_pushes',
                'name': 'Retry failed STK pushes (every 5 min)',
                'schedule_type': Schedule.MINUTES,
                'minutes': 5,
            },
        ]

        for s in schedules:
            func = s.pop('func')
            obj, created = Schedule.objects.get_or_create(func=func, defaults=s)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created schedule: {s["name"]}'))
            else:
                self.stdout.write(self.style.WARNING(f'Schedule already exists, skipped: {func}'))
