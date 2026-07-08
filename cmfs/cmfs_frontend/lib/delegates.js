import { api } from './api';

export async function getRegistrationOptions() {
  return api.get('/api/delegates/register/options/');
}

export async function publicRegister(body) {
  return api.post('/api/delegates/register/', body);
}

export async function getRegistrationStatus(registrationId) {
  return api.get(`/api/delegates/registration-status/${registrationId}/`);
}

export async function manualRegister(body) {
  return api.post('/api/delegates/manual/', body);
}

export async function getDelegate(delegateId) {
  return api.get(`/api/delegates/${delegateId}/`);
}

export async function getDelegatePayments(delegateId) {
  return api.get(`/api/delegates/${delegateId}/payments/`);
}

export async function getUnitDelegates(unitId) {
  return api.get(`/api/units/${unitId}/delegates/`);
}

export async function getUnitDelegatesSummary(unitId) {
  return api.get(`/api/units/${unitId}/delegates/summary/`);
}

/** POST /api/delegates/{delegateId}/send-reminder/ — Budget Creator or above. */
export async function sendPaymentReminder(delegateId) {
  return api.post(`/api/delegates/${delegateId}/send-reminder/`, {});
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Builds the absolute URL for a delegate's QR code PNG (qr_code_path is MEDIA_URL-relative, e.g. "/media/qr_codes/KER-STU-2026-0042.png"). */
export function getQrCodeUrl(delegate) {
  if (!delegate?.qr_code_path) return null;
  return `${API_BASE_URL}${delegate.qr_code_path}`;
}

/**
 * TEMPORARY fallback while Resend isn't configured (Phase 7 addendum):
 * hits GET /api/delegates/{delegateId}/qr/, which generates the QR on
 * the spot (bypassing Django Q2 + email entirely) and serves it as a
 * direct download. Remove once email delivery is confirmed working —
 * the QR is already emailed automatically at that point.
 */
export function getQrDownloadUrl(delegateId) {
  if (!delegateId) return null;
  return `${API_BASE_URL}/api/delegates/${delegateId}/qr/`;
}

export const CATEGORY_LABELS = {
  student: 'Student',
  kessat: 'Kessat',
  associate: 'Associate',
};

export const PAYMENT_STATUS_STYLES = {
  PENDING:    { label: 'Pending Payment', bg: 'bg-gray-100',   text: 'text-gray-600'   },
  NOT_PAID:   { label: 'Not Paid',        bg: 'bg-red-100',    text: 'text-red-700'    },
  INCOMPLETE: { label: 'Incomplete',      bg: 'bg-yellow-100', text: 'text-yellow-700' },
  COMPLETE:   { label: 'Complete',        bg: 'bg-green-100',  text: 'text-green-700'  },
  OVERPAID:   { label: 'Overpaid',        bg: 'bg-blue-100',   text: 'text-blue-700'   },
};

export function fmtKES(n) {
  return `KES ${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** Pulls the first error message out of a { field: [msg, ...] } validation_error payload. */
export function firstErrorMessage(errorData, fallback = 'Something went wrong. Please try again.') {
  if (!errorData) return fallback;
  const err = errorData.error;
  if (typeof err === 'string') return err;
  if (err && typeof err === 'object') {
    const firstKey = Object.keys(err)[0];
    const val = err[firstKey];
    return Array.isArray(val) ? val[0] : String(val);
  }
  return fallback;
}