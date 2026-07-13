import { api } from './api';

export async function getMyUnits() {
  return api.get('/api/my-units/');
}

export async function getPreloadedExpenseItems() {
  return api.get('/api/budget/expense-items/preloaded/');
}

export async function listBudgetIncome(unitId) {
  return api.get(`/api/units/${unitId}/budget/income/`);
}

export async function saveBudgetIncome(unitId, body) {
  return api.post(`/api/units/${unitId}/budget/income/`, body);
}

export async function updateBudgetIncome(incomeId, body) {
  return api.patch(`/api/budget/income/${incomeId}/`, body);
}

// offering/exhibition only — student/kessat/associate actuals are computed
// automatically from confirmed payments and rejected server-side here.
export async function recordBudgetIncomeActual(incomeId, actualTotal) {
  return api.patch(`/api/budget/income/${incomeId}/actual/`, { actual_total: actualTotal });
}

export async function deleteBudgetIncome(incomeId) {
  return api.del(`/api/budget/income/${incomeId}/`);
}

export async function listBudgetExpenses(unitId) {
  return api.get(`/api/units/${unitId}/budget/expenses/`);
}

export async function addBudgetExpense(unitId, body) {
  return api.post(`/api/units/${unitId}/budget/expenses/`, body);
}

export async function updateBudgetExpense(itemId, body) {
  return api.patch(`/api/budget/expenses/${itemId}/`, body);
}

export async function deleteBudgetExpense(itemId) {
  return api.del(`/api/budget/expenses/${itemId}/`);
}

export async function getBudgetSummary(unitId) {
  return api.get(`/api/units/${unitId}/budget/summary/`);
}

// ── Actuals & write-offs (Phase 9) ──────────────────────────────────────────────

export async function listActualExpenses(unitId) {
  return api.get(`/api/units/${unitId}/actuals/expenses/`);
}

/** body: {budget_expense_item_id, actual_qty, actual_unit_price, authorized_by, received_by, notes?} */
export async function recordActualExpense(unitId, body) {
  return api.post(`/api/units/${unitId}/actuals/expenses/`, body);
}

/** body: {item_name, category, unit?, actual_qty, actual_unit_price, authorized_by, received_by, notes?} */
export async function recordUnbudgetedExpense(unitId, body) {
  return api.post(`/api/units/${unitId}/actuals/unbudgeted/`, body);
}

export async function getActualsSummary(unitId) {
  return api.get(`/api/units/${unitId}/actuals/summary/`);
}

/** Removes a mis-keyed actual expense entry. If it was unbudgeted, its auto-created budget line is removed with it. */
export async function deleteActualExpense(actualExpenseId) {
  return api.del(`/api/budget/actuals/${actualExpenseId}/`);
}

export async function getOutstandingPayments(unitId) {
  return api.get(`/api/units/${unitId}/actuals/outstanding/`);
}

export async function chasePayment(delegateId) {
  return api.post(`/api/delegates/${delegateId}/chase/`, {});
}

/** body: {reason, totp_code} */
export async function writeOffDelegate(delegateId, reason, totpCode) {
  return api.post(`/api/delegates/${delegateId}/write-off/`, { reason, totp_code: totpCode });
}

export const INCOME_CATEGORIES = [
  { value: 'student', label: 'Students' },
  { value: 'kessat', label: 'Kessats' },
  { value: 'associate', label: 'Associates' },
  { value: 'offering', label: 'Offering' },
  { value: 'exhibition', label: 'Exhibition' },
];

export const EXPENSE_CATEGORIES = [
  { value: 'ACCOM', label: 'Accommodation' },
  { value: 'FOOD', label: 'Food' },
  { value: 'STAFF', label: 'Catering Staff' },
  { value: 'EQUIP', label: 'Equipment/Logistics' },
  { value: 'TRANS', label: 'Transport' },
  { value: 'SPEAK', label: 'Speaker Tokens' },
  { value: 'APPR', label: 'Workers & Appreciation' },
  { value: 'SECAD', label: 'Security & Admin' },
  { value: 'PRINT', label: 'Stationery/Printing' },
  { value: 'SUPP', label: 'Support' },
  { value: 'PREPOST', label: 'Pre/Post Convention' },
  { value: 'MISC', label: 'Miscellaneous' },
];

export function fmtKES(n) {
  return `KES ${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}