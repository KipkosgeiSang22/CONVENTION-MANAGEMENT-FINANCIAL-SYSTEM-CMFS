/**
 * FILE: cmfs/cmfs_frontend/pages/budget/actuals.js
 * ACTION: CREATE (Phase 9)
 *
 * Budget Creator: record actual expenses against budgeted items, or
 * unbudgeted spend (auto-creates its own UNB-{CATEGORY}-{SEQ} item).
 * Everyone else with unit access (Finance Viewer, heads, Super Admin):
 * read-only — same running totals + variance table, no entry forms.
 */
import { useEffect, useState } from 'react';
import Link from 'next/link';
import useAuth from '../../lib/useAuth';
import InactivityGuard from '../../components/InactivityGuard';
import {
  getMyUnits, listBudgetExpenses, listActualExpenses, recordActualExpense,
  recordUnbudgetedExpense, getActualsSummary, deleteActualExpense, EXPENSE_CATEGORIES, fmtKES,
} from '../../lib/budget';

export default function ActualsPage() {
  const { user, loading: authLoading } = useAuth();
  const canEdit = ['budget_creator', 'super_admin', 'national_head', 'regional_head', 'county_head'].includes(user?.role);

  const [units, setUnits] = useState(null);
  const [selectedUnitId, setSelectedUnitId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [budgetItems, setBudgetItems] = useState([]);
  const [actuals, setActuals] = useState([]);
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    if (!user) return;
    (async () => {
      setLoading(true);
      const res = await getMyUnits();
      if (res.ok) {
        setUnits(res.data);
        if (res.data.length === 1) setSelectedUnitId(res.data[0].unit_id);
      } else {
        setError(res.data?.error || 'Failed to resolve your convention unit.');
      }
      setLoading(false);
    })();
  }, [user]);

  useEffect(() => {
    if (!selectedUnitId) return;
    refreshAll();
  }, [selectedUnitId]);

  async function refreshAll() {
    setError('');
    const [budRes, actRes, sumRes] = await Promise.all([
      listBudgetExpenses(selectedUnitId),
      listActualExpenses(selectedUnitId),
      getActualsSummary(selectedUnitId),
    ]);
    if (budRes.ok) setBudgetItems(budRes.data.items || []);
    if (actRes.ok) setActuals(actRes.data.actual_expenses || []);
    if (sumRes.ok) setSummary(sumRes.data);
    if (!budRes.ok || !actRes.ok || !sumRes.ok) {
      setError(budRes.data?.error || actRes.data?.error || sumRes.data?.error || 'Failed to load actuals.');
    }
  }

  if (authLoading || !user || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <InactivityGuard>
      <div className="min-h-screen bg-gray-50">
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-3">
          <Link href="/budget" className="text-gray-400 hover:text-gray-600 text-sm">← Budget</Link>
          <span className="text-gray-300">/</span>
          <h1 className="text-xl font-bold text-gray-900">Actual Expenses</h1>
          {!canEdit && (
            <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
              Read-only
            </span>
          )}
          <Link href="/budget/outstanding" className="ml-auto text-sm text-blue-600 hover:underline">
            Outstanding Payments →
          </Link>
        </div>

        <div className="max-w-6xl mx-auto px-6 py-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-4 text-sm">{error}</div>
          )}

          {units && units.length === 0 && (
            <div className="text-center py-20 text-gray-400">
              <p className="font-medium text-gray-500">No live convention covers your area yet.</p>
            </div>
          )}

          {units && units.length > 1 && (
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-1">Select convention</label>
              <select
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-full max-w-md"
                value={selectedUnitId || ''}
                onChange={e => setSelectedUnitId(Number(e.target.value))}
              >
                <option value="" disabled>Choose a convention…</option>
                {units.map(u => (
                  <option key={u.unit_id} value={u.unit_id}>{u.convention_name} — {u.display_name}</option>
                ))}
              </select>
            </div>
          )}

          {selectedUnitId && summary && <SummaryBar summary={summary} />}

          {selectedUnitId && canEdit && (
            <EntryForms
              unitId={selectedUnitId}
              budgetItems={budgetItems}
              onChange={refreshAll}
            />
          )}

          {selectedUnitId && (
            <ActualsTable actuals={actuals} canEdit={canEdit} onChange={refreshAll} />
          )}
        </div>
      </div>
    </InactivityGuard>
  );
}

function SummaryBar({ summary }) {
  const isSurplus = Number(summary.surplus_deficit) >= 0;
  return (
    <div className="grid sm:grid-cols-3 gap-4 mb-6">
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <p className="text-xs text-gray-500 uppercase tracking-wide">Total Actual Income</p>
        <p className="text-lg font-semibold text-gray-900">{fmtKES(summary.total_actual_income)}</p>
      </div>
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <p className="text-xs text-gray-500 uppercase tracking-wide">Total Actual Expenses</p>
        <p className="text-lg font-semibold text-gray-900">{fmtKES(summary.total_actual_expenses)}</p>
      </div>
      <div className={`rounded-lg border p-4 ${isSurplus ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
        <p className="text-xs text-gray-500 uppercase tracking-wide">{isSurplus ? 'Surplus' : 'Deficit'}</p>
        <p className={`text-xl font-bold ${isSurplus ? 'text-green-700' : 'text-red-700'}`}>
          {fmtKES(Math.abs(summary.surplus_deficit))}
        </p>
      </div>
      {Number(summary.total_written_off) > 0 && (
        <div className="sm:col-span-3 bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 text-sm text-amber-700">
          {fmtKES(summary.total_written_off)} written off — outstanding balance reduced from{' '}
          {fmtKES(summary.total_outstanding_before_writeoffs)} to {fmtKES(summary.total_outstanding_after_writeoffs)}.
        </div>
      )}
    </div>
  );
}

function EntryForms({ unitId, budgetItems, onChange }) {
  const [mode, setMode] = useState('budgeted'); // budgeted | unbudgeted
  const [budgetItemId, setBudgetItemId] = useState('');
  const [itemName, setItemName] = useState('');
  const [category, setCategory] = useState('');
  const [unitLabel, setUnitLabel] = useState('');
  const [qty, setQty] = useState('');
  const [price, setPrice] = useState('');
  const [authorizedBy, setAuthorizedBy] = useState('');
  const [receivedBy, setReceivedBy] = useState('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [lastVoucher, setLastVoucher] = useState(null);

  function resetForm() {
    setBudgetItemId(''); setItemName(''); setCategory(''); setUnitLabel('');
    setQty(''); setPrice(''); setAuthorizedBy(''); setReceivedBy(''); setNotes('');
  }

  async function handleSubmit() {
    setFormError('');
    if (!qty || !price || !authorizedBy || !receivedBy) {
      setFormError('Quantity, unit price, authorized by, and received by are all required.');
      return;
    }

    setSaving(true);
    let res;
    if (mode === 'budgeted') {
      if (!budgetItemId) { setSaving(false); setFormError('Select a budgeted item.'); return; }
      res = await recordActualExpense(unitId, {
        budget_expense_item_id: Number(budgetItemId),
        actual_qty: qty, actual_unit_price: price,
        authorized_by: authorizedBy, received_by: receivedBy, notes,
      });
    } else {
      if (!itemName || !category) { setSaving(false); setFormError('Item name and category are required.'); return; }
      res = await recordUnbudgetedExpense(unitId, {
        item_name: itemName, category, unit: unitLabel,
        actual_qty: qty, actual_unit_price: price,
        authorized_by: authorizedBy, received_by: receivedBy, notes,
      });
    }
    setSaving(false);

    if (!res.ok) {
      const err = res.data?.error;
      setFormError(typeof err === 'string' ? err : Object.values(err || {})[0] || 'Could not record the expense.');
      return;
    }

    const voucher = res.data.actual_expense?.voucher_number;
    setLastVoucher(voucher);
    resetForm();
    onChange();
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-gray-900">Record Actual Expense</h2>
        {lastVoucher && (
          <span className="text-xs font-mono bg-green-50 text-green-700 border border-green-200 rounded px-2 py-1">
            Recorded as {lastVoucher}
          </span>
        )}
      </div>

      <div className="flex gap-2 mb-4">
        <button onClick={() => setMode('budgeted')}
          className={`text-xs px-3 py-1.5 rounded ${mode === 'budgeted' ? 'bg-blue-600 text-white' : 'bg-gray-100 border border-gray-300'}`}>
          Against Budgeted Item
        </button>
        <button onClick={() => setMode('unbudgeted')}
          className={`text-xs px-3 py-1.5 rounded ${mode === 'unbudgeted' ? 'bg-blue-600 text-white' : 'bg-gray-100 border border-gray-300'}`}>
          Unbudgeted Expense
        </button>
      </div>

      {mode === 'budgeted' ? (
        <select value={budgetItemId} onChange={e => setBudgetItemId(e.target.value)}
          className="w-full border border-gray-300 rounded px-2 py-2 text-sm mb-3">
          <option value="">Select a budgeted item…</option>
          {budgetItems.map(i => (
            <option key={i.id} value={i.id}>{i.item_code} — {i.item_name} (budgeted {fmtKES(i.estimated_total)})</option>
          ))}
        </select>
      ) : (
        <div className="grid grid-cols-3 gap-2 mb-3">
          <input placeholder="Item name" value={itemName} onChange={e => setItemName(e.target.value)}
            className="col-span-2 border border-gray-300 rounded px-2 py-2 text-sm" />
          <select value={category} onChange={e => setCategory(e.target.value)}
            className="border border-gray-300 rounded px-2 py-2 text-sm">
            <option value="">Category…</option>
            {EXPENSE_CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 mb-3">
        <input type="number" min="0" placeholder="Actual quantity" value={qty} onChange={e => setQty(e.target.value)}
          className="border border-gray-300 rounded px-2 py-2 text-sm" />
        <input type="number" min="0" placeholder="Actual unit price (KES)" value={price} onChange={e => setPrice(e.target.value)}
          className="border border-gray-300 rounded px-2 py-2 text-sm" />
      </div>

      <div className="grid grid-cols-2 gap-2 mb-3">
        <input placeholder="Authorized by" value={authorizedBy} onChange={e => setAuthorizedBy(e.target.value)}
          className="border border-gray-300 rounded px-2 py-2 text-sm" />
        <input placeholder="Received by" value={receivedBy} onChange={e => setReceivedBy(e.target.value)}
          className="border border-gray-300 rounded px-2 py-2 text-sm" />
      </div>

      <input placeholder="Notes (optional)" value={notes} onChange={e => setNotes(e.target.value)}
        className="w-full border border-gray-300 rounded px-2 py-2 text-sm mb-3" />

      {formError && <p className="text-xs text-red-600 mb-3">{formError}</p>}

      <button onClick={handleSubmit} disabled={saving}
        className="bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50">
        {saving ? 'Recording…' : 'Record Expense'}
      </button>
    </div>
  );
}

function ActualsTable({ actuals, canEdit, onChange }) {
  const totalVariance = actuals.reduce((s, a) => s + Number(a.variance || 0), 0);
  const [deletingId, setDeletingId] = useState(null);

  async function handleDelete(a) {
    const warning = a.is_unbudgeted
      ? `Delete voucher ${a.voucher_number} (${a.item_name})? Since this was an unbudgeted expense, its budget line will be removed too. This cannot be undone.`
      : `Delete voucher ${a.voucher_number} (${a.item_name})? This cannot be undone.`;
    if (!window.confirm(warning)) return;

    setDeletingId(a.id);
    const res = await deleteActualExpense(a.id);
    setDeletingId(null);
    if (res.ok) {
      onChange();
    } else {
      alert(res.data?.error?.error || res.data?.error || 'Could not delete this entry.');
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <h2 className="font-semibold text-gray-900 mb-4">Actual vs Budget</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-100">
              <th className="py-1.5 pr-3">Voucher</th>
              <th className="py-1.5 pr-3">Item</th>
              <th className="py-1.5 pr-3 text-right">Budgeted</th>
              <th className="py-1.5 pr-3 text-right">Actual</th>
              <th className="py-1.5 pr-3 text-right">Variance</th>
              <th className="py-1.5 pr-3">Authorized / Received</th>
              <th className="py-1.5">Entered By</th>
              {canEdit && <th className="py-1.5"></th>}
            </tr>
          </thead>
          <tbody>
            {actuals.map(a => {
              const variance = Number(a.variance || 0);
              return (
                <tr key={a.id} className="border-b border-gray-50">
                  <td className="py-2 pr-3 font-mono text-gray-500">{a.voucher_number}</td>
                  <td className="py-2 pr-3">
                    {a.item_name}
                    <span className="ml-1 text-gray-400 font-mono text-[11px]">
                      {a.item_code}{a.is_unbudgeted && ' · unbudgeted'}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-right text-gray-500">{fmtKES(a.estimated_total)}</td>
                  <td className="py-2 pr-3 text-right font-medium">{fmtKES(a.actual_total)}</td>
                  <td className={`py-2 pr-3 text-right font-medium ${variance > 0 ? 'text-red-600' : variance < 0 ? 'text-green-600' : 'text-gray-400'}`}>
                    {variance > 0 ? '+' : ''}{fmtKES(variance)}
                  </td>
                  <td className="py-2 pr-3 text-gray-500">{a.authorized_by} / {a.received_by}</td>
                  <td className="py-2 text-gray-500">{a.entered_by_name}</td>
                  {canEdit && (
                    <td className="py-2 pl-2 text-right">
                      <button
                        onClick={() => handleDelete(a)}
                        disabled={deletingId === a.id}
                        className="text-red-600 hover:underline disabled:opacity-50"
                      >
                        {deletingId === a.id ? 'Deleting…' : 'Delete'}
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
            {actuals.length === 0 && (
              <tr><td colSpan={canEdit ? 8 : 7} className="py-6 text-center text-gray-400">No actual expenses recorded yet.</td></tr>
            )}
          </tbody>
          {actuals.length > 0 && (
            <tfoot>
              <tr className="border-t border-gray-200 font-semibold">
                <td colSpan={4} className="py-2 pr-3 text-right">Total Variance</td>
                <td className={`py-2 pr-3 text-right ${totalVariance > 0 ? 'text-red-600' : totalVariance < 0 ? 'text-green-600' : 'text-gray-500'}`}>
                  {totalVariance > 0 ? '+' : ''}{fmtKES(totalVariance)}
                </td>
                <td colSpan={canEdit ? 3 : 2}></td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  );
}
