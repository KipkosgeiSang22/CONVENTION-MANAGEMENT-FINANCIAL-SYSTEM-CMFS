"""
FILE: cmfs/cmfs_backend/conventions/tasks.py
ACTION: CREATE (Phase 3)

Django Q2 background tasks:
  - auto_transition_convention_status     (daily cron)
  - send_convention_published_notifications
  - send_convention_started_notification
  - send_convention_ended_notification
  - generate_opening_day_reports
  - generate_final_reports               (on FINANCIALLY_CLOSED)

These are called with django_q.tasks.async_task() or scheduled via
Django Q2's Schedule model. Only stubs that can be filled in later phases
for actual report generation (Phase 10).
"""

import logging
from datetime import date

from django.utils import timezone as dj_tz

logger = logging.getLogger(__name__)


# ── Auto-transition (daily cron) ───────────────────────────────────────────────

def auto_transition_convention_status():
    """
    Daily cron task: auto-transition conventions based on start_date / end_date.

    Schedule in Django Q2:
        from django_q.models import Schedule
        Schedule.objects.create(
            func='conventions.tasks.auto_transition_convention_status',
            schedule_type=Schedule.DAILY,
            name='Auto-transition convention status',
        )
    """
    from .models import Convention

    today = date.today()
    now = dj_tz.now()
    transitioned = []

    # OPEN → ACTIVE on start_date
    open_conventions = Convention.objects.filter(
        status__in=(Convention.STATUS_OPEN, Convention.STATUS_DRAFT),
        start_date__lte=today,
    )
    for conv in open_conventions:
        conv.status = Convention.STATUS_ACTIVE
        conv.started_at = now
        conv.save(update_fields=['status', 'started_at'])
        transitioned.append(f'ACTIVATED: {conv.name} (id={conv.id})')
        try:
            send_convention_started_notification(conv.id)
        except Exception as e:
            logger.error(f'Error sending started notification for conv {conv.id}: {e}')

    # ACTIVE → ENDED on end_date
    active_conventions = Convention.objects.filter(
        status=Convention.STATUS_ACTIVE,
        end_date__lt=today,
    )
    for conv in active_conventions:
        conv.status = Convention.STATUS_ENDED
        conv.ended_at = now
        conv.is_registration_open = False
        conv.save(update_fields=['status', 'ended_at', 'is_registration_open'])
        transitioned.append(f'ENDED: {conv.name} (id={conv.id})')
        try:
            send_convention_ended_notification(conv.id)
        except Exception as e:
            logger.error(f'Error sending ended notification for conv {conv.id}: {e}')

    if transitioned:
        logger.info('auto_transition_convention_status: ' + '; '.join(transitioned))
    else:
        logger.info('auto_transition_convention_status: no transitions needed today.')

    return transitioned


# ── Notification tasks ─────────────────────────────────────────────────────────

def send_convention_published_notifications(convention_id: int):
    """
    Called when a convention is published (DRAFT → OPEN).
    Sends invitation emails to all heads assigned to convention units.
    """
    from .models import Convention, ConventionUnit
    from auth_app.models import User
    from auth_app.emails import send_invitation_email
    from django.conf import settings

    try:
        convention = Convention.objects.prefetch_related('units').get(pk=convention_id)
    except Convention.DoesNotExist:
        logger.error(f'send_convention_published_notifications: convention {convention_id} not found')
        return

    heads = _get_convention_head_users(convention)
    for head in heads:
        try:
            setup_url = f"{settings.FRONTEND_URL}/auth/setup?token={head.setup_token}" if head.setup_token else settings.FRONTEND_URL
            send_invitation_email(head, setup_url)
            logger.info(f'Sent invitation to {head.email} for convention {convention.name}')
        except Exception as e:
            logger.error(f'Failed to send invitation to head {head.email}: {e}')


def send_convention_started_notification(convention_id: int):
    """
    Called when convention status → ACTIVE.
    Emails all heads and Super Admin: "Convention started — reports available."
    """
    from .models import Convention
    from auth_app.models import User

    try:
        convention = Convention.objects.prefetch_related('units').get(pk=convention_id)
    except Convention.DoesNotExist:
        logger.error(f'send_convention_started_notification: convention {convention_id} not found')
        return

    recipients = _get_convention_recipient_emails(convention)
    subject = f'[KSCF] Convention Started: {convention.name}'
    body = (
        f"The convention '{convention.name}' has started.\n\n"
        f"Start Date: {convention.start_date}\n"
        f"End Date:   {convention.end_date}\n\n"
        f"The Opening Day Reports button is now available on your dashboard.\n\n"
        f"Gate module is now ACTIVE.\n"
    )
    _send_bulk_email(recipients, subject, body)
    logger.info(f'send_convention_started_notification: sent to {len(recipients)} recipients')


def send_convention_ended_notification(convention_id: int):
    """
    Called when convention status → ENDED.
    Emails all heads and Super Admin.
    Triggers final M-Pesa reconciliation (stub — implemented in Phase 7).
    """
    from .models import Convention

    try:
        convention = Convention.objects.prefetch_related('units').get(pk=convention_id)
    except Convention.DoesNotExist:
        logger.error(f'send_convention_ended_notification: convention {convention_id} not found')
        return

    recipients = _get_convention_recipient_emails(convention)
    subject = f'[KSCF] Convention Ended: {convention.name}'
    body = (
        f"The convention '{convention.name}' has ended.\n\n"
        f"Registration is now CLOSED and the gate module has been DEACTIVATED.\n\n"
        f"Please review outstanding payments and complete expense entries before\n"
        f"proceeding to Financial Close.\n"
    )
    _send_bulk_email(recipients, subject, body)
    logger.info(f'send_convention_ended_notification: sent to {len(recipients)} recipients')

    # Stub: trigger M-Pesa reconciliation (Phase 7)
    logger.info(f'TODO Phase 7: trigger M-Pesa reconciliation for convention {convention_id}')


def generate_opening_day_reports(convention_id: int, triggered_by: int = None):
    """
    Generates and emails:
      - Current Income Summary
      - Current Budget vs Actuals snapshot
      - Delegate Register
      - Outstanding Payments Report

    Full report generation is implemented in Phase 10. This is the task stub
    that wires the Q2 async call and logging.
    """
    from .models import Convention

    try:
        convention = Convention.objects.get(pk=convention_id)
    except Convention.DoesNotExist:
        logger.error(f'generate_opening_day_reports: convention {convention_id} not found')
        return

    logger.info(
        f'generate_opening_day_reports: Generating opening day reports for '
        f'"{convention.name}" (triggered_by={triggered_by})'
    )

    # TODO Phase 10: generate Excel/PDF reports via OpenPyXL/ReportLab
    # TODO Phase 10: email reports to appropriate heads

    logger.info(f'generate_opening_day_reports: STUB complete — implement in Phase 10')


def generate_final_reports(convention_id: int):
    """
    Called on FINANCIALLY_CLOSED transition.
    Generates all 9 final reports as Excel + PDF and distributes by email.

    Full implementation in Phase 10. Stub here to allow Phase 3 to wire correctly.
    """
    from .models import Convention

    try:
        convention = Convention.objects.get(pk=convention_id)
    except Convention.DoesNotExist:
        logger.error(f'generate_final_reports: convention {convention_id} not found')
        return

    logger.info(f'generate_final_reports: STUB — queuing report generation for "{convention.name}"')

    # TODO Phase 10: generate and email:
    #   1. Final Income & Expenditure Statement (Excel + PDF)
    #   2. Final Budgeted vs Actuals Report (Excel + PDF)
    #   3. Payment Voucher Log PV01–PVxx (Excel + PDF)
    #   4. Income Summary with receipt batches (Excel + PDF)
    #   5. Delegate Register with payment history (Excel + PDF)
    #   6. Attendance Report (Excel + PDF)
    #   7. Unbudgeted Expenses Report (Excel + PDF)
    #   8. Outstanding/Written-Off Payments Report (Excel + PDF)
    #   9. Surplus/Deficit Summary (Excel + PDF)
    # Plus regional/national consolidated reports where applicable.

    logger.info(f'generate_final_reports: STUB complete — implement in Phase 10')


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_convention_head_users(convention):
    """
    Returns the head-role Users (national_head/regional_head/county_head)
    whose own county_id/region_id matches this convention's units — the
    same matching logic that drives view access (see conventions/permissions.py
    and conventions/views.py list filtering). Replaces the old head_user_id
    lookup now that heads are matched automatically rather than assigned
    per-unit at creation time.
    """
    from auth_app.models import User

    if convention.scope == 'national':
        return list(User.objects.filter(role='national_head'))

    county_ids = [unit.county_id for unit in convention.units.all() if unit.county_id]
    region_ids = [unit.region_id for unit in convention.units.all() if unit.region_id]

    heads = []
    if region_ids:
        heads += list(User.objects.filter(role='regional_head', region_id__in=region_ids))
    if county_ids:
        heads += list(User.objects.filter(role='county_head', county_id__in=county_ids))
    return heads


def _get_convention_recipient_emails(convention) -> list:
    """
    Returns email addresses of all heads for this convention + all Super Admins.
    """
    from auth_app.models import User

    emails = set()

    # Super Admins always receive everything
    for u in User.objects.filter(role='super_admin').values_list('email', flat=True):
        emails.add(u)

    # Heads matched to this convention's units by county_id/region_id
    for head in _get_convention_head_users(convention):
        emails.add(head.email)

    return list(emails)


def _send_bulk_email(recipients: list, subject: str, body: str):
    """Send an email to multiple recipients via Resend."""
    if not recipients:
        return

    import resend
    from django.conf import settings

    resend.api_key = settings.RESEND_API_KEY
    FROM = getattr(settings, 'RESEND_FROM_EMAIL', 'noreply@kscf.or.ke')

    for email in recipients:
        try:
            resend.Emails.send({
                'from': FROM,
                'to': [email],
                'subject': subject,
                'text': body,
            })
        except Exception as e:
            logger.error(f'_send_bulk_email: failed to send to {email}: {e}')
