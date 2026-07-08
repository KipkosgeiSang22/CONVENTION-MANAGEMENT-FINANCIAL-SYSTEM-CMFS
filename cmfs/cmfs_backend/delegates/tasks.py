"""
FILE: cmfs/cmfs_backend/delegates/tasks.py
ACTION: CREATE (Phase 6)

QR code generation and email sending are built in Phase 7. These are the
stubs that Phase 6 queues into so nothing needs to change structurally
when Phase 7 fills them in — matches the pattern used in
conventions/tasks.py for report generation.
"""

import logging

logger = logging.getLogger(__name__)


def on_payment_confirmed(delegate_id: int):
    """
    Called (via django_q async_task) the moment a delegate's first payment
    is CONFIRMED (cash or M-Pesa). Delegate ID has already been generated
    and registration_status set to 'active' by the caller.

    Phase 7 will implement:
      - generate_qr_code(delegate_id)
      - send_confirmation_email(delegate_id)
    """
    from .models import Delegate

    try:
        delegate = Delegate.objects.get(pk=delegate_id)
    except Delegate.DoesNotExist:
        logger.error(f'on_payment_confirmed: delegate {delegate_id} not found')
        return

    logger.info(
        f'on_payment_confirmed: delegate {delegate.delegate_id} ({delegate.email}) — '
        f'QR generation + confirmation email queued for Phase 7'
    )
    # TODO Phase 7: async_task('delegates.tasks.generate_and_send_qr', delegate_id)


def on_payment_failed(payment_id: int):
    """
    Called when an M-Pesa payment attempt FAILS or TIMES OUT.
    Phase 7 will implement send_payment_failure_email(delegate_id).
    """
    from payments.models import Payment

    try:
        payment = Payment.objects.select_related('delegate').get(pk=payment_id)
    except Payment.DoesNotExist:
        logger.error(f'on_payment_failed: payment {payment_id} not found')
        return

    logger.info(
        f'on_payment_failed: payment {payment.id} for delegate '
        f'{payment.delegate.email} — failure email queued for Phase 7'
    )
    # TODO Phase 7: async_task('auth_app.emails.send_payment_failure_email', payment.delegate_id)