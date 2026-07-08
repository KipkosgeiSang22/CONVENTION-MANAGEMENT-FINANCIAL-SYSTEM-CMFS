"""
FILE: cmfs/cmfs_backend/delegates/emails.py
ACTION: CREATE (Phase 7)

Delegate-facing Resend emails: confirmation (with QR attached), payment
failure, and payment reminders. All three are Django Q2 tasks — never
called synchronously from a view — and each returns True/False so
cmfs_backend.utils.task_retry can tell a real success from a failure and
retry up to 3 times before giving up and logging it to the audit log.
"""
import logging

import resend
from django.conf import settings

from cmfs_backend.utils.task_retry import run_with_retries
from .qr import qr_absolute_path

logger = logging.getLogger(__name__)

FROM_ADDRESS = getattr(settings, 'RESEND_FROM_EMAIL', 'noreply@kscf.or.ke')


def _send(to: str, subject: str, html: str, attachments=None) -> bool:
    resend.api_key = settings.RESEND_API_KEY
    payload = {'from': FROM_ADDRESS, 'to': [to], 'subject': subject, 'html': html}
    if attachments:
        payload['attachments'] = attachments
    try:
        resend.Emails.send(payload)
        return True
    except Exception as exc:
        logger.error('Resend error sending to %s: %s', to, exc)
        return False


def _payment_summary_html(delegate) -> str:
    if delegate.balance_owed > 0:
        return (
            f"<p>Amount paid so far: <strong>KES {delegate.total_paid:,.2f}</strong></p>"
            f"<p>Balance remaining: <strong>KES {delegate.balance_owed:,.2f}</strong></p>"
        )
    return f"<p>Fee paid in full: <strong>KES {delegate.total_paid:,.2f}</strong></p>"


# ── Confirmation email (with QR attached) ───────────────────────────────────────

def _send_confirmation_email_once(delegate_id: int) -> bool:
    from .models import Delegate

    try:
        delegate = Delegate.objects.select_related('convention', 'county').get(pk=delegate_id)
    except Delegate.DoesNotExist:
        logger.error(f'send_confirmation_email: delegate {delegate_id} not found')
        return False

    attachments = []
    qr_path = qr_absolute_path(delegate)
    if qr_path.exists():
        with open(qr_path, 'rb') as f:
            # Resend's Python SDK takes attachment bytes as a plain list of ints.
            attachments.append({'filename': f'{delegate.delegate_id}.png', 'content': list(f.read())})
    else:
        logger.warning(f'send_confirmation_email: QR file missing for {delegate.delegate_id}, sending without it')

    html = f"""
    <h2>You're registered!</h2>
    <p>Hello {delegate.full_name},</p>
    <p>Your registration for <strong>{delegate.convention.name}</strong> is confirmed.</p>
    <p>Delegate ID: <strong>{delegate.delegate_id}</strong></p>
    <p>Category: {delegate.get_category_display()}</p>
    <p>County: {delegate.county.name}</p>
    {_payment_summary_html(delegate)}
    <p>Your QR code is attached — please bring it (printed or on your phone) to the gate.</p>
    """
    return _send(delegate.email, f'KSCF Convention Registration Confirmed — {delegate.delegate_id}', html, attachments)


def send_confirmation_email(delegate_id: int) -> bool:
    """Django Q2 task. Queued from delegates.tasks.generate_and_send_qr once the QR file exists."""
    return run_with_retries(_send_confirmation_email_once, delegate_id, task_name='send_confirmation_email')


# ── Payment failure email ───────────────────────────────────────────────────────

def _send_payment_failure_email_once(delegate_id: int) -> bool:
    from .models import Delegate

    try:
        delegate = Delegate.objects.get(pk=delegate_id)
    except Delegate.DoesNotExist:
        logger.error(f'send_payment_failure_email: delegate {delegate_id} not found')
        return False

    latest_payment = delegate.payments.order_by('-timestamp').first()
    reason = (latest_payment.notes if latest_payment else '') or 'The payment could not be completed.'
    retry_url = f"{settings.FRONTEND_URL}/register/status/{delegate.id}?amount={delegate.fee_amount}"

    html = f"""
    <h2>Payment Not Completed</h2>
    <p>Hello {delegate.full_name},</p>
    <p>Your M-Pesa payment for the convention registration did not go through.</p>
    <p>Reason: {reason}</p>
    <p><a href="{retry_url}">Click here to try again</a></p>
    """
    return _send(delegate.email, 'KSCF Convention — Payment Not Completed', html)


def send_payment_failure_email(delegate_id: int) -> bool:
    """Django Q2 task. Queued from delegates.tasks.on_payment_failed."""
    return run_with_retries(_send_payment_failure_email_once, delegate_id, task_name='send_payment_failure_email')


# ── Payment reminder email ──────────────────────────────────────────────────────

def _send_payment_reminder_email_once(delegate_id: int) -> bool:
    from .models import Delegate

    try:
        delegate = Delegate.objects.select_related('convention').get(pk=delegate_id)
    except Delegate.DoesNotExist:
        logger.error(f'send_payment_reminder_email: delegate {delegate_id} not found')
        return False

    if delegate.balance_owed <= 0:
        logger.info(f'send_payment_reminder_email: delegate {delegate.delegate_id} has no balance, skipping')
        return True  # nothing to send — not a failure

    html = f"""
    <h2>Payment Reminder</h2>
    <p>Hello {delegate.full_name},</p>
    <p>This is a reminder that you have an outstanding balance of
       <strong>KES {delegate.balance_owed:,.2f}</strong> for
       <strong>{delegate.convention.name}</strong>
       ({delegate.convention.start_date} – {delegate.convention.end_date}).</p>
    <p>Please settle this with your County Budget Creator, or via M-Pesa, before the convention.</p>
    """
    return _send(delegate.email, 'KSCF Convention — Payment Reminder', html)


def send_payment_reminder_email(delegate_id: int) -> bool:
    """Django Q2 task. Queued manually by a Budget Creator — see delegates.views.SendPaymentReminderView."""
    return run_with_retries(_send_payment_reminder_email_once, delegate_id, task_name='send_payment_reminder_email')
