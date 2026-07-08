"""
FILE: cmfs/cmfs_backend/payments/tasks.py
ACTION: CREATE (Phase 6)

Django Q2 background tasks:
  - initiate_stk_push_task(payment_id)   — fired immediately on registration
  - reconcile_mpesa_payments()           — nightly cron at 02:00
  - retry_failed_stk_pushes()            — every 5 minutes

Schedule reconcile_mpesa_payments and retry_failed_stk_pushes via Django
Q2's Schedule model (see bottom of this file for the snippet).
"""

import logging
from datetime import timedelta

from django.utils import timezone as dj_tz

from .daraja import initiate_stk_push, DarajaError
from .services import fail_payment

logger = logging.getLogger(__name__)

STALE_AFTER_MINUTES = 30     # no callback received within this window → timeout
MAX_INITIATE_RETRIES = 3


def initiate_stk_push_task(payment_id: int):
    """
    Fired via async_task() right after a Payment row is created with
    status='initiated'. Calls Daraja; on success stores the returned
    CheckoutRequestID as the Payment's idempotency_key (so the callback
    can be correlated back to this row) and moves status to 'pending'.
    On failure, marks the payment 'failed' — retry_failed_stk_pushes()
    will pick it back up.
    """
    from .models import Payment

    try:
        payment = Payment.objects.select_related('delegate').get(pk=payment_id)
    except Payment.DoesNotExist:
        logger.error(f'initiate_stk_push_task: payment {payment_id} not found')
        return

    if payment.status != 'initiated':
        logger.info(f'initiate_stk_push_task: payment {payment_id} no longer initiated, skipping')
        return

    delegate = payment.delegate
    try:
        response = initiate_stk_push(
            phone=delegate.parent_phone,
            amount=payment.amount_paid,
            account_reference=delegate.delegate_id or f'REG{delegate.id}',
            transaction_desc=f'KSCF Convention Registration — {delegate.full_name}',
        )
        checkout_request_id = response.get('CheckoutRequestID')
        if checkout_request_id:
            payment.idempotency_key = checkout_request_id
        payment.status = 'pending'
        payment.save()
        logger.info(f'initiate_stk_push_task: STK push sent for payment {payment.id}')

    except DarajaError as e:
        logger.error(f'initiate_stk_push_task: Daraja error for payment {payment.id}: {e}')
        fail_payment(payment, reason=f'STK push failed: {e}')
    except Exception as e:
        logger.error(f'initiate_stk_push_task: unexpected error for payment {payment.id}: {e}')
        fail_payment(payment, reason=f'STK push error: {e}')


def retry_failed_stk_pushes():
    """
    Every 5 minutes: re-attempts STK push for payments that failed purely
    because our own request to Daraja didn't go through (network/API
    error) — never for payments the user actively declined or that timed
    out waiting for a PIN, which Safaricom would have already reported
    via callback with a non-zero ResultCode.

    Retry count is tracked inline via the `notes` field (`retry:N`) since
    the schema doesn't carry a dedicated counter.
    """
    from .models import Payment

    # failure_code='' means Daraja never returned a ResultCode at all — our own
    # STK push request itself never went through (network/API error). A
    # non-empty failure_code means Daraja DID respond (user cancelled, wrong
    # PIN, insufficient balance, etc.) — those should not be blindly retried.
    candidates = Payment.objects.filter(status='failed', payment_method='mpesa', failure_code='')
    retried = 0

    for payment in candidates:
        retry_count = _extract_retry_count(payment.notes)
        if retry_count >= MAX_INITIATE_RETRIES:
            continue

        payment.status = 'initiated'
        payment.notes = f'{payment.notes} | retry:{retry_count + 1}'.strip(' |')
        payment.save()
        initiate_stk_push_task(payment.id)
        retried += 1

    logger.info(f'retry_failed_stk_pushes: retried {retried} payment(s)')
    return retried


def reconcile_mpesa_payments():
    """
    Nightly cron at 02:00. Any M-Pesa payment stuck in 'pending' with no
    resolution for STALE_AFTER_MINUTES is actively checked against
    Daraja's STK Query API (sync_payment_from_daraja) before being given
    up on — the same fallback the registration-status polling endpoint
    uses in real time, run here as a catch-all safety net for anything
    the frontend never polled long enough to resolve (e.g. the browser
    tab was closed). Only falls back to 'timeout' if Daraja still has no
    definitive answer.
    """
    from .models import Payment
    from .services import sync_payment_from_daraja

    cutoff = dj_tz.now() - timedelta(minutes=STALE_AFTER_MINUTES)
    stale = Payment.objects.filter(
        payment_method='mpesa', status='pending', timestamp__lt=cutoff,
    )

    confirmed = failed = timed_out = 0
    for payment in stale:
        outcome = sync_payment_from_daraja(payment)
        if outcome == 'confirmed':
            confirmed += 1
        elif outcome == 'failed':
            failed += 1
        else:
            payment.status = 'timeout'
            payment.save()
            timed_out += 1

    # Anything still 'initiated' this long never even reached Daraja (our
    # own STK push call failed silently) — no CheckoutRequestID exists to
    # query, so these just time out directly.
    for payment in Payment.objects.filter(payment_method='mpesa', status='initiated', timestamp__lt=cutoff):
        payment.status = 'timeout'
        payment.save()
        timed_out += 1

    logger.info(f'reconcile_mpesa_payments: {confirmed} confirmed, {failed} failed, {timed_out} timed out')
    return {'confirmed': confirmed, 'failed': failed, 'timed_out': timed_out}


def _extract_retry_count(notes: str) -> int:
    import re
    matches = re.findall(r'retry:(\d+)', notes or '')
    return int(matches[-1]) if matches else 0


# ── Scheduling (run once, e.g. in a management command or Django admin) ───────
#
# from django_q.models import Schedule
# Schedule.objects.get_or_create(
#     func='payments.tasks.reconcile_mpesa_payments',
#     defaults={'schedule_type': Schedule.DAILY, 'name': 'Nightly M-Pesa reconciliation (02:00)'},
# )
# Schedule.objects.get_or_create(
#     func='payments.tasks.retry_failed_stk_pushes',
#     defaults={'schedule_type': Schedule.MINUTES, 'minutes': 5, 'name': 'Retry failed STK pushes'},
# )