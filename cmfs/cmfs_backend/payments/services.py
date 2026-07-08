"""
FILE: cmfs/cmfs_backend/payments/services.py
ACTION: CREATE (Phase 6)

Shared logic for what happens when a Payment becomes CONFIRMED, regardless
of whether it arrived via cash, manual registration, or the M-Pesa
callback. Keeps Delegate ID generation + activation in exactly one place.
"""

import logging
from django_q.tasks import async_task

from auth_app.audit import log as audit_log

logger = logging.getLogger(__name__)


def confirm_payment(payment, amount=None, mpesa_transaction_id=None):
    """
    Marks `payment` CONFIRMED and, if this is the delegate's first
    confirmed payment, activates the delegate and generates their
    Delegate ID. Safe to call multiple times for installment payments —
    activation only happens once.
    """
    from delegates.utils import generate_delegate_id

    if amount is not None:
        payment.amount_paid = amount
    if mpesa_transaction_id:
        payment.mpesa_transaction_id = mpesa_transaction_id
    payment.status = 'confirmed'
    payment.save()

    delegate = payment.delegate
    first_confirmation = delegate.registration_status == 'pending'

    if first_confirmation:
        delegate.registration_status = 'active'
        delegate.delegate_id = generate_delegate_id(delegate)
        delegate.save()

        audit_log(
            action='delegate_activated',
            detail=f'Delegate {delegate.delegate_id} activated via payment id={payment.id}',
        )

        try:
            async_task('delegates.tasks.on_payment_confirmed', delegate.id)
        except Exception as e:
            logger.error(f'confirm_payment: failed to queue on_payment_confirmed: {e}')

    audit_log(
        action='payment_confirmed',
        detail=f'Payment id={payment.id} confirmed for delegate id={delegate.id}, amount={payment.amount_paid}',
    )

    return delegate


def fail_payment(payment, reason: str = '', result_code: str = ''):
    payment.status = 'failed'
    if result_code:
        payment.failure_code = result_code
    if reason:
        payment.notes = (payment.notes + ' | ' if payment.notes else '') + reason
    payment.save()

    audit_log(
        action='payment_failed',
        detail=f'Payment id={payment.id} failed: {reason}',
    )

    try:
        async_task('delegates.tasks.on_payment_failed', payment.id)
    except Exception as e:
        logger.error(f'fail_payment: failed to queue on_payment_failed: {e}')


# Daraja's STK Query ResultCode values that mean "definitely not paid" —
# anything else non-zero is treated the same way (generic failure), this
# list just documents the common ones for readability.
_QUERY_FAILURE_CODES = {'1032', '1037', '1025', '1001', '2001'}


def sync_payment_from_daraja(payment) -> str:
    """
    Actively queries Daraja for this payment's real status instead of
    waiting for the callback — required when MPESA_CALLBACK_URL isn't
    publicly reachable (e.g. local/private-network development with no
    tunnel). Called from the registration-status polling endpoint and
    from the nightly reconciliation job.

    Returns one of: 'confirmed', 'failed', 'still_pending', 'skipped',
    'query_error'.

    IMPORTANT: the Query API does not return the M-Pesa receipt number
    or confirmed amount — only the callback does. A payment confirmed
    this way is recorded with the amount that was originally requested
    and mpesa_transaction_id left blank; if the callback arrives later
    (e.g. once a public URL is configured), MpesaCallbackView backfills
    the receipt number onto this same row rather than double-processing
    it.
    """
    from .daraja import query_stk_status, DarajaError

    if payment.payment_method != 'mpesa' or payment.status not in ('pending',):
        return 'skipped'

    # idempotency_key is only a real CheckoutRequestID once the STK push
    # actually went out — before that it's still our own uuid4 placeholder.
    if not payment.idempotency_key or len(payment.idempotency_key) < 10:
        return 'skipped'

    try:
        result = query_stk_status(payment.idempotency_key)
    except DarajaError as e:
        logger.info(f'sync_payment_from_daraja: payment {payment.id} not resolved yet: {e}')
        return 'query_error'

    result_code = str(result.get('ResultCode', ''))

    if result_code == '0':
        confirm_payment(payment, amount=payment.amount_paid, mpesa_transaction_id=None)
        payment.notes = (payment.notes + ' | ' if payment.notes else '') + 'Confirmed via STK query (no callback received).'
        payment.save()
        return 'confirmed'

    if result_code in _QUERY_FAILURE_CODES:
        fail_payment(payment, reason=result.get('ResultDesc', f'STK query ResultCode={result_code}'), result_code=result_code)
        return 'failed'

    # Anything else non-zero (e.g. 4999 "still under processing", or any
    # code Safaricom hasn't documented for us) is NOT a confirmed failure —
    # only the specific codes above mean "definitely not paid". Leave the
    # payment pending; the next poll, retry, or the callback itself will
    # resolve it.
    return 'still_pending'