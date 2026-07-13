/**
 * FILE: cmfs/cmfs_frontend/pages/budget/index.js
 * ACTION: CREATE (Phase 5)
 *
 * Budget income + expense entry for a resolved ConventionUnit.
 * unit_id is resolved via GET /api/my-units/ — if more than one live
 * convention covers this user's geography, they pick which one first.
 * Budget Creator: full edit. Everyone else with access (Finance Viewer,
 * heads, Super Admin): read-only.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import useAuth from '../../lib/useAuth';
import InactivityGuard from '../../components/InactivityGuard';
import {
  getMyUnits, getPreloadedExpenseItems, listBudgetIncome, saveBudgetIncome,
  deleteBudgetIncome, listBudgetExpenses, addBudgetExpense, deleteBudgetExpense,
  getBudgetSummary, recordBudgetIncomeActual, INCOME_CATEGORIES, fmtKES,
} from '../../lib/budget';

export default function BudgetPage() {
  const { user, loading: authLoading } = useAuth();
  const canEdit = ['budget_creator', 'super_admin', 'national_head', 'regional_head', 'county_head'].includes(user?.role);

  const [units, setUnits] = useState(null);
  const [selectedUnitId, setSelectedUnitId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [incomes, setIncomes] = useState([]);
  const [expenseItems, setExpenseItems] = useState([]);
  const [preloaded, setPreloaded] = useState([]);
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
    getPreloadedExpenseItems().then(res => { if (res.ok) setPreloaded(res.data.items || []); });
  }, [selectedUnitId]);

  async function refreshAll() {
    setError('');
    const [incRes, expRes, sumRes] = await Promise.all([
      listBudgetIncome(selectedUnitId),
      listBudgetExpenses(selectedUnitId),
      getBudgetSummary(selectedUnitId),
    ]);
    if (incRes.ok) setIncomes(incRes.data.incomes || []);
    if (expRes.ok) setExpenseItems(expRes.data.items || []);
    if (sumRes.ok) setSummary(sumRes.data);
    if (!incRes.ok || !expRes.ok || !sumRes.ok) {
      setError(incRes.data?.error || expRes.data?.error || sumRes.data?.error || 'Failed to load budget.');
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
          <Link href="/dashboard" className="text-gray-400 hover:text-gray-600 text-sm">← Dashboard</Link>
          <span className="text-gray-300">/</span>
          <h1 className="text-xl font-bold text-gray-900">Budget</h1>
          {!canEdit && (
            <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
              Read-only
            </span>
          )}
          <div className="ml-auto flex items-center gap-4">
            <Link href="/budget/actuals" className="text-sm text-blue-600 hover:underline">
              Actual Expenses →
            </Link>
            <Link href="/budget/outstanding" className="text-sm text-blue-600 hover:underline">
              Outstanding Payments →
            </Link>
          </div>
        </div>

        <div className="max-w-5xl mx-auto px-6 py-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-4 text-sm">{error}</div>
          )}

          {units && units.length === 0 && (
            <div className="text-center py-20 text-gray-400">
              <div className="text-5xl mb-3">📊</div>
              <p className="font-medium text-gray-500">No live convention covers your area yet.</p>
              <p className="text-sm mt-1">Budget entry opens once a convention including your unit is published.</p>
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
                  <option key={u.unit_id} value={u.unit_id}>
                    {u.convention_name} — {u.display_name} ({u.status})
                  </option>
                ))}
              </select>
            </div>
          )}

          {selectedUnitId && summary && (
            <SurplusDeficitBar summary={summary} />
          )}

          {selectedUnitId && (
            <div className="grid md:grid-cols-2 gap-6 mt-6">
              <IncomeSection
                unitId={selectedUnitId}
                incomes={incomes}
                canEdit={canEdit}
                onChange={refreshAll}
              />
              
              <ExpenseSection
                unitId={selectedUnitId}
                items={expenseItems}
                preloaded={preloaded}
                canEdit={canEdit}
                onChange={refreshAll}
              />
            </div>
          )}
        </div>
      </div>
    </InactivityGuard>
  );
}

function SurplusDeficitBar({ summary }) {
  const isSurplus = Number(summary.surplus_deficit) >= 0;
  return (
    <div className={`rounded-lg border p-5 flex flex-wrap items-center justify-between gap-4 ${
      isSurplus ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
    }`}>
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide">Total Estimated Income</p>
        <p className="text-lg font-semibold text-gray-900">{fmtKES(summary.total_estimated_income)}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide">
          Total Estimated Expenses <span className="text-gray-400">(incl. 5% misc)</span>
        </p>
        <p className="text-lg font-semibold text-gray-900">{fmtKES(summary.total_estimated_expenses)}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide">{isSurplus ? 'Surplus' : 'Deficit'}</p>
        <p className={`text-2xl font-bold ${isSurplus ? 'text-green-700' : 'text-red-700'}`}>
          {fmtKES(Math.abs(summary.surplus_deficit))}
        </p>
      </div>
    </div>
  );
}

function IncomeSection({ unitId, incomes, canEdit, onChange }) {
  const [saving, setSaving] = useState(null);
  const [savingActual, setSavingActual] = useState(null);
  const [form, setForm] = useState({});
  const [actualForm, setActualForm] = useState({});

  function byCategory(cat) {
    return incomes.find(i => i.category === cat);
  }

  async function handleSave(cat) {
    setSaving(cat);
    const isFreeText = cat === 'offering' || cat === 'exhibition';
    const body = isFreeText
      ? { category: cat, estimated_total: form[cat]?.total ?? byCategory(cat)?.estimated_total ?? 0 }
      : { category: cat, estimated_count: form[cat]?.count ?? byCategory(cat)?.estimated_count ?? 0 };
    const res = await saveBudgetIncome(unitId, body);
    setSaving(null);
    if (res.ok) onChange();
  }

  // offering/exhibition aren't tied to any delegate/payment, so — unlike
  // student/kessat/associate, whose actuals are always computed live from
  // confirmed payments — there's no automatic way to know what was actually
  // collected. Whoever counts the offering/exhibition takings records it here.
  async function handleSaveActual(cat) {
    const existing = byCategory(cat);
    if (!existing) return;
    const value = actualForm[cat] ?? existing.actual_total ?? 0;
    setSavingActual(cat);
    const res = await recordBudgetIncomeActual(existing.id, value);
    setSavingActual(null);
    if (res.ok) onChange();
  }

  const total = incomes.reduce((s, i) => s + Number(i.estimated_total || 0), 0);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <h2 className="font-semibold text-gray-900 mb-4">Income Estimates</h2>
      <div className="space-y-3">
        {INCOME_CATEGORIES.map(({ value, label }) => {
          const existing = byCategory(value);
          const isFreeText = value === 'offering' || value === 'exhibition';
          return (
            <div key={value} className="flex items-center gap-2 flex-wrap">
              <span className="w-24 text-sm text-gray-600">{label}</span>
              {isFreeText ? (
                <input
                  type="number" min="0" disabled={!canEdit}
                  placeholder="Amount (KES)"
                  defaultValue={existing?.estimated_total ?? ''}
                  onChange={e => setForm(f => ({ ...f, [value]: { total: e.target.value } }))}
                  className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm disabled:bg-gray-50"
                />
              ) : (
                <input
                  type="number" min="0" disabled={!canEdit}
                  placeholder="Estimated count"
                  defaultValue={existing?.estimated_count ?? ''}
                  onChange={e => setForm(f => ({ ...f, [value]: { count: e.target.value } }))}
                  className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm disabled:bg-gray-50"
                />
              )}
              <span className="w-28 text-right text-sm font-medium text-gray-700">
                {fmtKES(existing?.estimated_total ?? 0)}
              </span>
              {canEdit && (
                <button
                  onClick={() => handleSave(value)}
                  disabled={saving === value}
                  className="text-xs bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving === value ? '…' : 'Save'}
                </button>
              )}

              {/* Actual collected — offering/exhibition only, once the line exists */}
              {isFreeText && existing && (
                <div className="w-full flex items-center gap-2 pl-24">
                  <span className="text-xs text-gray-400 w-20">Actual:</span>
                  <input
                    type="number" min="0" disabled={!canEdit}
                    placeholder="Actual collected (KES)"
                    defaultValue={existing?.actual_total ?? ''}
                    onChange={e => setActualForm(f => ({ ...f, [value]: e.target.value }))}
                    className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm disabled:bg-gray-50"
                  />
                  {canEdit && (
                    <button
                      onClick={() => handleSaveActual(value)}
                      disabled={savingActual === value}
                      className="text-xs bg-gray-700 text-white px-2 py-1 rounded hover:bg-gray-800 disabled:opacity-50"
                    >
                      {savingActual === value ? '…' : 'Record Actual'}
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-4 pt-3 border-t border-gray-100 flex justify-between text-sm font-semibold">
        <span>Total Estimated Income</span>
        <span>{fmtKES(total)}</span>
      </div>
    </div>
  );
}

function ExpenseSection({ unitId, items, preloaded, canEdit, onChange }) {
  const [mode, setMode] = useState('preloaded'); // preloaded | custom
  const [preloadedId, setPreloadedId] = useState('');
  const [customName, setCustomName] = useState('');
  const [customCategory, setCustomCategory] = useState('');
  const [qty, setQty] = useState('');
  const [price, setPrice] = useState('');
  const [days, setDays] = useState('1');
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  const total = items.reduce((s, i) => s + Number(i.estimated_total || 0), 0);

  async function handleAdd() {
    setFormError('');
    if (!qty || !price) { setFormError('Quantity and unit price are required.'); return; }
    const body = {
      quantity: qty, unit_price: price, days: days || 1,
      ...(mode === 'preloaded'
        ? { preloaded_item_id: Number(preloadedId) }
        : { item_name: customName, category: customCategory }),
    };
    setSaving(true);
    const res = await addBudgetExpense(unitId, body);
    setSaving(false);
    if (!res.ok) { setFormError(res.data?.error?.[Object.keys(res.data?.error || {})[0]] || 'Could not add item.'); return; }
    setPreloadedId(''); setCustomName(''); setCustomCategory(''); setQty(''); setPrice(''); setDays('1');
    onChange();
  }

  async function handleDelete(id) {
    const res = await deleteBudgetExpense(id);
    if (res.ok) onChange();
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <h2 className="font-semibold text-gray-900 mb-4">Expense Items</h2>

      {canEdit && (
        <div className="border border-gray-200 rounded-lg p-3 mb-4 bg-gray-50">
          <div className="flex gap-2 mb-2">
            <button onClick={() => setMode('preloaded')}
              className={`text-xs px-2 py-1 rounded ${mode === 'preloaded' ? 'bg-blue-600 text-white' : 'bg-white border border-gray-300'}`}>
              Pre-loaded item
            </button>
            <button onClick={() => setMode('custom')}
              className={`text-xs px-2 py-1 rounded ${mode === 'custom' ? 'bg-blue-600 text-white' : 'bg-white border border-gray-300'}`}>
              Add Custom Item
            </button>
          </div>

          {mode === 'preloaded' ? (
            <select value={preloadedId} onChange={e => setPreloadedId(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1 text-sm mb-2">
              <option value="">Select an item…</option>
              {preloaded.map(p => (
                <option key={p.id} value={p.id}>{p.name} ({p.category})</option>
              ))}
            </select>
          ) : (
            <div className="grid grid-cols-2 gap-2 mb-2">
              <input placeholder="Item name" value={customName} onChange={e => setCustomName(e.target.value)}
                className="border border-gray-300 rounded px-2 py-1 text-sm" />
              <input placeholder="Category code e.g. FOOD" value={customCategory}
                onChange={e => setCustomCategory(e.target.value.toUpperCase())}
                className="border border-gray-300 rounded px-2 py-1 text-sm" />
            </div>
          )}

          <div className="grid grid-cols-3 gap-2 mb-2">
            <input type="number" min="0" placeholder="Qty" value={qty} onChange={e => setQty(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1 text-sm" />
            <input type="number" min="0" placeholder="Unit price" value={price} onChange={e => setPrice(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1 text-sm" />
            <input type="number" min="1" placeholder="Days" value={days} onChange={e => setDays(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1 text-sm" />
          </div>

          {formError && <p className="text-xs text-red-600 mb-2">{formError}</p>}

          <button onClick={handleAdd} disabled={saving}
            className="text-xs bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700 disabled:opacity-50">
            {saving ? 'Adding…' : 'Add Item'}
          </button>
        </div>
      )}

      <div className="max-h-80 overflow-y-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-100">
              <th className="py-1">Code</th>
              <th className="py-1">Item</th>
              <th className="py-1 text-right">Qty</th>
              <th className="py-1 text-right">Unit Price</th>
              <th className="py-1 text-right">Total</th>
              {canEdit && <th></th>}
            </tr>
          </thead>
          <tbody>
            {items.map(i => (
              <tr key={i.id} className="border-b border-gray-50">
                <td className="py-1.5 font-mono text-gray-500">{i.item_code}</td>
                <td className="py-1.5">{i.item_name}{i.is_custom && <span className="ml-1 text-gray-400">(custom)</span>}</td>
                <td className="py-1.5 text-right">{i.estimated_qty}</td>
                <td className="py-1.5 text-right">{fmtKES(i.unit_price)}</td>
                <td className="py-1.5 text-right font-medium">{fmtKES(i.estimated_total)}</td>
                {canEdit && (
                  <td className="py-1.5 text-right">
                    <button onClick={() => handleDelete(i.id)} className="text-red-500 hover:text-red-700">✕</button>
                  </td>
                )}
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan={canEdit ? 6 : 5} className="py-6 text-center text-gray-400">No expense items yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 pt-3 border-t border-gray-100 flex justify-between text-sm font-semibold">
        <span>Total Direct Expenses</span>
        <span>{fmtKES(total)}</span>
      </div>
    </div>
  );
}