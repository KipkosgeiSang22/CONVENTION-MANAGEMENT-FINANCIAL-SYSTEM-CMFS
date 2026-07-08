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