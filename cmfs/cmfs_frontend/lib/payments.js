import { api } from './api';

/**
 * Triggers/retries an M-Pesa STK Push for a delegate.
 * Works both unauthenticated (public retry, only while the delegate's
 * registration is still PENDING) and authenticated (Budget Creator
 * collecting an installment on an active delegate).
 */
export async function initiateMpesa(delegateId, amount) {
  return api.post('/api/payments/mpesa/initiate/', { delegate: delegateId, amount });
}

/** Budget Creator only. */
export async function recordCashPayment(delegateId, amount, notes = '') {
  return api.post('/api/payments/cash/', { delegate: delegateId, amount, notes });
}