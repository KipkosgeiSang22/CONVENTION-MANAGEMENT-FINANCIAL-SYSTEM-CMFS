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
  { value: 'SECAD', label: 'Security & Admin' },
  { value: 'PRINT', label: 'Stationery/Printing' },
  { value: 'SUPP', label: 'Support' },
  { value: 'PREPOST', label: 'Pre/Post Convention' },
  { value: 'MISC', label: 'Miscellaneous' },
];

export function fmtKES(n) {
  return `KES ${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}