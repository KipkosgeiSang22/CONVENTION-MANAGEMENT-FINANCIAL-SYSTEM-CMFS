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
import os
from datetime import date, timedelta

from django.conf import settings
from django.utils import timezone as dj_tz
from django_q.tasks import async_task

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
        status__in=(Convention.STATUS_OPEN),
        start_date__lte=today,
    )
    for conv in open_conventions:
        conv.status = Convention.STATUS_ACTIVE
        conv.started_at = now
        conv.save(update_fields=['status', 'started_at'])
        transitioned.append(f'ACTIVATED: {conv.name} (id={conv.id})')
        try:
            async_task('conventions.tasks.send_convention_started_notification', conv.id)
        except Exception as e:
            logger.error(f'Error queuing started notification for conv {conv.id}: {e}')

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
            async_task('conventions.tasks.send_convention_ended_notification', conv.id)
        except Exception as e:
            logger.error(f'Error queuing ended notification for conv {conv.id}: {e}')

    if transitioned:
        logger.info('auto_transition_convention_status: ' + '; '.join(transitioned))
    else:
        logger.info('auto_transition_convention_status: no transitions needed today.')

    return transitioned


def check_annual_summary_trigger():
    """
    Daily cron task: for every December convention that reached
    FINANCIALLY_CLOSED at least 7 days ago, generate (once per calendar
    year) the Annual Summary report and email it to Super Admin.

    Schedule in Django Q2:
        from django_q.models import Schedule
        Schedule.objects.create(
            func='conventions.tasks.check_annual_summary_trigger',
            schedule_type=Schedule.DAILY,
            name='Check annual summary trigger',
        )
    """
    from .models import Convention
    from reports.models import AnnualSummary

    now = dj_tz.now()
    cutoff = now - timedelta(days=7)

    due_conventions = Convention.objects.filter(
        status=Convention.STATUS_FINANCIALLY_CLOSED,
        end_date__month=12,
        financially_closed_at__isnull=False,
        financially_closed_at__lte=cutoff,
    )

    years_triggered = set()
    for conv in due_conventions:
        year = conv.end_date.year
        if year in years_triggered:
            continue
        already_generated = AnnualSummary.objects.filter(year=year, status='generated').exists()
        if already_generated:
            continue
        years_triggered.add(year)
        try:
            generate_annual_summary(year)
            logger.info(f'check_annual_summary_trigger: generated annual summary for {year}')
        except Exception as e:
            logger.error(f'check_annual_summary_trigger: failed for year {year}: {e}')

    return sorted(years_triggered)


# ── Notification tasks ─────────────────────────────────────────────────────────

def send_convention_published_notifications(convention_id: int):
    """
    Called when a convention is published (DRAFT → OPEN).
    Sends invitation emails to all heads assigned to convention units.
    """
    from .models import Convention, ConventionUnit

    try:
        convention = Convention.objects.prefetch_related('units').get(pk=convention_id)
    except Convention.DoesNotExist:
        logger.error(f'send_convention_published_notifications: convention {convention_id} not found')
        return

    heads = _get_convention_head_users(convention)
    for head in heads:
        if not head.setup_token:
            # Already set up — nothing new to invite them to; the started/
            # ended notifications below are what keeps them informed.
            logger.info(f'send_convention_published_notifications: {head.email} already set up, skipping')
            continue
        try:
            async_task('auth_app.emails.send_invitation_email', head.id)
            logger.info(f'Queued invitation email to {head.email} for convention {convention.name}')
        except Exception as e:
            logger.error(f'Failed to queue invitation to head {head.email}: {e}')


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

    # Registration just closed — run an immediate reconciliation pass rather
    # than waiting for the 02:00 nightly cron (payments.tasks.reconcile_mpesa_payments).
    try:
        async_task('payments.tasks.reconcile_mpesa_payments')
        logger.info(f'send_convention_ended_notification: queued reconcile_mpesa_payments for convention {convention_id}')
    except Exception as e:
        logger.error(f'send_convention_ended_notification: failed to queue reconciliation: {e}')


def generate_opening_day_reports(convention_id: int, triggered_by: int = None):
    """
    Generates and emails:
      - Current Income Summary
      - Current Budget vs Actuals snapshot
      - Delegate Register
      - Outstanding Payments Report

    Delegates to reports.generators for the actual Excel/PDF generation,
    then emails each recipient the report files they're entitled to see
    (Phase 11 — same distribution rule as generate_final_reports) as
    attachments, alongside a link to view them in-app.
    """
    from .models import Convention
    from reports.generators import generate_reports_for_convention

    try:
        convention = Convention.objects.get(pk=convention_id)
    except Convention.DoesNotExist:
        logger.error(f'generate_opening_day_reports: convention {convention_id} not found')
        return

    logger.info(
        f'generate_opening_day_reports: Generating opening day reports for '
        f'"{convention.name}" (triggered_by={triggered_by})'
    )

    reports = generate_reports_for_convention(convention, report_type='opening_day', generated_by_id=triggered_by)
    failed = [r for r in reports if r.status == 'failed']
    if failed:
        logger.error(f'generate_opening_day_reports: {len(failed)} report file(s) failed to generate')

    body = (
        f"Opening day reports for '{convention.name}' have been generated.\n\n"
        f"Log in to the CMFS dashboard to view and download them, or see the attachments below.\n"
    )
    _distribute_reports_by_email(
        convention, report_type='opening_day',
        subject=f'[KSCF] Opening Day Reports Available: {convention.name}', body=body,
    )

    logger.info(f'generate_opening_day_reports: complete — {len(reports)} report files ({len(failed)} failed)')


def generate_final_reports(convention_id: int, triggered_by: int = None):
    """
    Called on FINANCIALLY_CLOSED transition.
    Generates the overall report + one report per ConventionUnit (Excel + PDF
    each — see reports.generators) and distributes by email per the
    Report Distribution table (County Head -> their county reports; Regional
    Head -> regional consolidated; National Head -> national consolidated;
    Finance Viewer -> county-level; Super Admin -> everything) — every
    recipient's email carries the actual report file(s) as attachments,
    scoped to exactly what they're allowed to access.
    """
    from .models import Convention
    from reports.generators import generate_reports_for_convention

    try:
        convention = Convention.objects.get(pk=convention_id)
    except Convention.DoesNotExist:
        logger.error(f'generate_final_reports: convention {convention_id} not found')
        return

    logger.info(f'generate_final_reports: generating final reports for "{convention.name}"')

    reports = generate_reports_for_convention(convention, report_type='final', generated_by_id=triggered_by)
    failed = [r for r in reports if r.status == 'failed']
    if failed:
        logger.error(f'generate_final_reports: {len(failed)} report file(s) failed to generate')

    body = (
        f"Final reports for '{convention.name}' are ready following financial close.\n\n"
        f"Your reports are attached. You can also log in to the CMFS dashboard to view and re-download them.\n"
    )
    _distribute_reports_by_email(
        convention, report_type='final',
        subject=f'[KSCF] Final Reports — {convention.name}', body=body,
    )

    logger.info(f'generate_final_reports: complete — {len(reports)} report files ({len(failed)} failed)')


def generate_annual_summary(year: int, triggered_by: int = None):
    """
    Aggregates every FINANCIALLY_CLOSED convention ending in `year` into
    one Annual Summary (Excel + PDF — see reports.generators), then queues
    one background email task per Super Admin (via async_task, processed
    by the Q cluster) with the files attached. Safe to call more than once
    for the same year (re-generates and re-queues the emails).
    """
    from reports.generators import generate_annual_summary_files
    from auth_app.models import User

    logger.info(f'generate_annual_summary: generating annual summary for {year}')
    summary = generate_annual_summary_files(year, triggered_by=triggered_by)

    if summary.status != 'generated':
        logger.error(f'generate_annual_summary: generation failed for {year}: {summary.error_message}')
        return summary

    attachments = _build_file_attachments([
        (f'annual-summary-{year}.xlsx', summary.xlsx_path),
        (f'annual-summary-{year}.pdf', summary.pdf_path),
    ])

    admin_emails = list(User.objects.filter(role='super_admin').values_list('email', flat=True))
    subject = f'[KSCF] Annual Summary Report — {year}'
    body = (
        f"The Annual Summary Report for {year} is ready — covering every convention financially "
        f"closed this year (delegate totals, income/expenditure, surplus/deficit per county, "
        f"year-on-year comparison, top counties, collection efficiency, unbudgeted and written-off "
        f"amounts). See the attached files, or log in to the CMFS dashboard to download them.\n"
    )
    for email in admin_emails:
        async_task('conventions.tasks._send_email_with_attachments', email, subject, body, attachments)

    logger.info(f'generate_annual_summary: complete for {year} — queued email to {len(admin_emails)} Super Admin(s)')
    return summary


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


def _get_convention_finance_viewers(convention):
    """
    Finance Viewers matched to this convention the same way heads are
    (their own county_id/region_id, or national scope if they carry
    neither) — mirrors auth_app.permissions.user_can_access_unit's
    finance_viewer branch. Used so the Report Distribution table's
    "Finance Viewer -> county-level reports" row actually gets emailed,
    not just visible on login.
    """
    from auth_app.models import User

    county_ids = [unit.county_id for unit in convention.units.all() if unit.county_id]
    region_ids = [unit.region_id for unit in convention.units.all() if unit.region_id]

    viewers = list(User.objects.filter(role='finance_viewer', county_id__in=county_ids)) if county_ids else []
    viewers += list(User.objects.filter(role='finance_viewer', region_id__in=region_ids)) if region_ids else []
    if convention.scope == 'national':
        viewers += list(User.objects.filter(role='finance_viewer', county_id__isnull=True, region_id__isnull=True))
    return viewers


def _reports_for_recipient(convention, user, report_type):
    """Every generated Report of `report_type` for this convention that `user`
    is allowed to access, per the same rule reports.views uses for downloads."""
    from reports.models import Report
    from reports.views import _can_access_report

    reports = Report.objects.filter(convention=convention, report_type=report_type, status='generated')
    return [r for r in reports if _can_access_report(user, r)]


def _build_report_attachments(reports) -> list:
    """Reads each Report's file off disk into a Resend attachment dict,
    using the same human-readable, collision-free filename the download
    endpoint uses (see reports.views._download_filename)."""
    from reports.views import _download_filename

    attachments = []
    for r in reports:
        if not r.file_path:
            continue
        abs_path = os.path.join(settings.MEDIA_ROOT, r.file_path)
        if not os.path.exists(abs_path):
            logger.warning(f'_build_report_attachments: file missing on disk for report {r.id}: {abs_path}')
            continue
        with open(abs_path, 'rb') as f:
            attachments.append({'filename': _download_filename(r), 'content': list(f.read())})
    return attachments


def _build_file_attachments(name_path_pairs) -> list:
    """Like _build_report_attachments, but for arbitrary (filename, relative_path)
    pairs — used for the Annual Summary, which isn't backed by a Report row."""
    attachments = []
    for filename, rel_path in name_path_pairs:
        if not rel_path:
            continue
        abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
        if not os.path.exists(abs_path):
            logger.warning(f'_build_file_attachments: file missing on disk: {abs_path}')
            continue
        with open(abs_path, 'rb') as f:
            attachments.append({'filename': filename, 'content': list(f.read())})
    return attachments


def _distribute_reports_by_email(convention, report_type, subject, body):
    """
    Queues `subject`/`body` to every recipient in the Report Distribution
    table as a separate background task (via async_task, processed by the
    Q cluster) — each with only the report files that recipient is allowed
    to access attached:
      - Super Admin: every generated report for this convention/report_type
      - National/Regional/County Head: their own accessible reports
      - Finance Viewer: their own accessible reports (county-level)

    Attachment scoping (which files each recipient gets) is resolved here,
    synchronously, since it's just DB queries + reading small files off
    disk. Only the actual email send — the slow, occasionally-flaky part
    (a call to the Resend API) — is deferred to the background.
    """
    from reports.models import Report
    from auth_app.models import User

    all_reports = list(Report.objects.filter(convention=convention, report_type=report_type, status='generated'))
    admin_attachments = _build_report_attachments(all_reports)
    for email in User.objects.filter(role='super_admin').values_list('email', flat=True):
        async_task('conventions.tasks._send_email_with_attachments', email, subject, body, admin_attachments)

    for head in _get_convention_head_users(convention):
        head_reports = _reports_for_recipient(convention, head, report_type)
        async_task('conventions.tasks._send_email_with_attachments', head.email, subject, body, _build_report_attachments(head_reports))

    for viewer in _get_convention_finance_viewers(convention):
        viewer_reports = _reports_for_recipient(convention, viewer, report_type)
        async_task('conventions.tasks._send_email_with_attachments', viewer.email, subject, body, _build_report_attachments(viewer_reports))


def _send_email_with_attachments(to_email: str, subject: str, body: str, attachments: list):
    """Sends one email to one recipient, with file attachments if any, retrying
    up to 3 times (same retry/audit-log contract as _send_bulk_email)."""
    if not to_email:
        return

    import resend
    from cmfs_backend.utils.task_retry import run_with_retries

    resend.api_key = settings.RESEND_API_KEY
    FROM = getattr(settings, 'RESEND_FROM_EMAIL', 'noreply@kscf.or.ke')

    def _send_one():
        try:
            payload = {'from': FROM, 'to': [to_email], 'subject': subject, 'text': body}
            if attachments:
                payload['attachments'] = attachments
            resend.Emails.send(payload)
            return True
        except Exception as e:
            logger.error(f'_send_email_with_attachments: failed to send to {to_email}: {e}')
            return False

    run_with_retries(_send_one, task_name=f'report_email:{subject}:{to_email}')


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
    """Send an email to multiple recipients via Resend, retrying each send up to 3 times."""
    if not recipients:
        return

    import resend
    from django.conf import settings
    from cmfs_backend.utils.task_retry import run_with_retries

    resend.api_key = settings.RESEND_API_KEY
    FROM = getattr(settings, 'RESEND_FROM_EMAIL', 'noreply@kscf.or.ke')

    def _send_one(email):
        try:
            resend.Emails.send({
                'from': FROM,
                'to': [email],
                'subject': subject,
                'text': body,
            })
            return True
        except Exception as e:
            logger.error(f'_send_bulk_email: failed to send to {email}: {e}')
            return False

    for email in recipients:
        run_with_retries(_send_one, email, task_name=f'bulk_email:{subject}')
