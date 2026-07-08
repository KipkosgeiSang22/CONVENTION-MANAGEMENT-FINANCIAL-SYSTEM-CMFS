"""
FILE: cmfs/cmfs_backend/delegates/tasks.py
ACTION: MODIFY (Phase 7)

Phase 6 left these as logging-only stubs queued into by
payments.services.confirm_payment / fail_payment. Phase 7 fills them in
for real: QR generation, confirmation email, failure email, and a
Budget-Creator-triggered payment reminder.
"""

import logging
from django_q.tasks import async_task

logger = logging.getLogger(__name__)


def on_payment_confirmed(delegate_id: int):
    """
    Called (via django_q async_task) the moment a delegate first payment
    is CONFIRMED (cash or M-Pesa). Delegate ID has already been generated
    and registration_status set to active by the caller (see
    payments.services.confirm_payment).
    """
    from .models import Delegate

    try:
        delegate = Delegate.objects.get(pk=delegate_id)
    except Delegate.DoesNotExist:
        logger.error(f"on_payment_confirmed: delegate {delegate_id} not found")
        return

    logger.info(
        f"on_payment_confirmed: delegate {delegate.delegate_id} ({delegate.email}) - "
        f"queuing QR generation + confirmation email"
    )
    async_task("delegates.tasks.generate_and_send_qr", delegate_id)


def generate_and_send_qr(delegate_id: int):
    """
    Single Q2 task that generates the QR PNG and then sends the
    confirmation email with it attached - kept as one task (rather than
    two separately-queued tasks) so the email step can never run before
    the file it needs to attach exists. If QR generation ultimately
    fails after its own retries, the confirmation email still goes out
    (without the attachment) rather than being silently dropped.
    """
    from .qr import generate_qr_code
    from .emails import send_confirmation_email

    if not generate_qr_code(delegate_id):
        logger.error(f"generate_and_send_qr: QR generation failed for delegate {delegate_id}; sending confirmation without it")

    send_confirmation_email(delegate_id)


def on_payment_failed(payment_id: int):
    """
    Called when an M-Pesa payment attempt FAILS or TIMES OUT.
    """
    from payments.models import Payment

    try:
        payment = Payment.objects.select_related("delegate").get(pk=payment_id)
    except Payment.DoesNotExist:
        logger.error(f"on_payment_failed: payment {payment_id} not found")
        return

    logger.info(
        f"on_payment_failed: payment {payment.id} for delegate "
        f"{payment.delegate.email} - queuing failure email"
    )
    async_task("delegates.emails.send_payment_failure_email", payment.delegate_id)


def send_payment_reminder_task(delegate_id: int):
    """
    Queued from delegates.views.SendPaymentReminderView (a Budget
    Creator action) - reminders are sent at the Budget Creator
    discretion, not on any automatic schedule.
    """
    async_task("delegates.emails.send_payment_reminder_email", delegate_id)
