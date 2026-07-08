/**
 * FILE: cmfs/cmfs_frontend/pages/delegates/index.js
 * ACTION: CREATE (Phase 6)
 *
 * Staff-facing delegate management: summary counts (County Head) +
 * full list with payment-status badges (Budget Creator), plus a quick
 * "Record Cash Payment" action for Budget Creators. unit_id resolved
 * via GET /api/my-units/, same pattern as the Budget module.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import useAuth from '../../lib/useAuth';
import InactivityGuard from '../../components/InactivityGuard';
import {
  getUnitDelegates, getUnitDelegatesSummary, CATEGORY_LABELS, PAYMENT_STATUS_STYLES, fmtKES,
} from '../../lib/delegates';
import { recordCashPayment } from '../../lib/payments';
import { getMyUnits } from '../../lib/budget';

const EDIT_ROLES = ['budget_creator', 'super_admin', 'national_head', 'regional_head', 'county_head'];

export default function DelegatesPage() {
  const { user, loading: authLoading } = useAuth();
  const canRecordPayment = user?.role === 'budget_creator' || EDIT_ROLES.includes(user?.role);

  const [units, setUnits] = useState(null);
  const [selectedUnitId, setSelectedUnitId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [delegates, setDelegates] = useState([]);
  const [summary, setSummary] = useState(null);
  const [payingId, setPayingId] = useState(null);

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
    const [listRes, summaryRes] = await Promise.all([
      getUnitDelegates(selectedUnitId),
      getUnitDelegatesSummary(selectedUnitId),
    ]);
    if (listRes.ok) setDelegates(listRes.data.delegates || []);
    if (summaryRes.ok) setSummary(summaryRes.data);
    if (!listRes.ok || !summaryRes.ok) {
      setError(listRes.data?.error || summaryRes.data?.error || 'Failed to load delegates.');
    }
  }

  async function handleRecordCash(delegate) {
    const amountStr = window.prompt(
      `Record a cash payment for ${delegate.full_name} (balance: ${fmtKES(delegate.balance_owed)}):`,
      Math.max(delegate.balance_owed, 0) || ''
    );
    if (!amountStr) return;
    const amount = Number(amountStr);
    if (!amount || amount <= 0) return;

    setPayingId(delegate.id);
    const res = await recordCashPayment(delegate.id, amount);
    setPayingId(null);
    if (res.ok) {
      refreshAll();
    } else {
      alert(res.data?.error?.error || res.data?.error || 'Could not record payment.');
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
          <h1 className="text-xl font-bold text-gray-900">Delegates</h1>
          {user.role === 'budget_creator' && (
            <Link href="/delegates/manual"
              className="ml-auto text-sm bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700">
              + Manual Registration
            </Link>
          )}
        </div>

        <div className="max-w-5xl mx-auto px-6 py-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-4 text-sm">{error}</div>
          )}

          {units && units.length === 0 && (
            <div className="text-center py-20 text-gray-400">
              <div className="text-5xl mb-3">🧑‍🤝‍🧑</div>
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
                  <option key={u.unit_id} value={u.unit_id}>
                    {u.convention_name} — {u.display_name} ({u.status})
                  </option>
                ))}
              </select>
            </div>
          )}

          {selectedUnitId && summary && <SummaryCards summary={summary} />}

          {selectedUnitId && (
            <div className="bg-white border border-gray-200 rounded-lg mt-6 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                  <tr>
                    <th className="text-left px-4 py-2">Delegate ID</th>
                    <th className="text-left px-4 py-2">Name</th>
                    <th className="text-left px-4 py-2">Category</th>
                    <th className="text-right px-4 py-2">Balance</th>
                    <th className="text-left px-4 py-2">Status</th>
                    {canRecordPayment && <th className="px-4 py-2"></th>}
                  </tr>
                </thead>
                <tbody>
                  {delegates.map(d => {
                    const badge = PAYMENT_STATUS_STYLES[d.payment_status] || PAYMENT_STATUS_STYLES.PENDING;
                    return (
                      <tr key={d.id} className="border-t border-gray-100">
                        <td className="px-4 py-2.5 font-mono text-gray-500">{d.delegate_id || '—'}</td>
                        <td className="px-4 py-2.5">{d.full_name}</td>
                        <td className="px-4 py-2.5">{CATEGORY_LABELS[d.category] || d.category}</td>
                        <td className="px-4 py-2.5 text-right font-medium">{fmtKES(d.balance_owed)}</td>
                        <td className="px-4 py-2.5">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${badge.bg} ${badge.text}`}>
                            {badge.label}
                          </span>
                        </td>
                        {canRecordPayment && (
                          <td className="px-4 py-2.5 text-right">
                            {d.balance_owed > 0 && (
                              <button onClick={() => handleRecordCash(d)} disabled={payingId === d.id}
                                className="text-xs text-blue-600 hover:underline disabled:opacity-50">
                                {payingId === d.id ? 'Recording…' : 'Record Cash Payment'}
                              </button>
                            )}
                          </td>
                        )}
                      </tr>
                    );
                  })}
                  {delegates.length === 0 && (
                    <tr>
                      <td colSpan={canRecordPayment ? 6 : 5} className="px-4 py-8 text-center text-gray-400">
                        No delegates registered yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </InactivityGuard>
  );
}

function SummaryCards({ summary }) {
  const cards = [
    { key: 'COMPLETE', label: 'Complete' },
    { key: 'INCOMPLETE', label: 'Incomplete' },
    { key: 'NOT_PAID', label: 'Not Paid' },
    { key: 'PENDING', label: 'Pending' },
    { key: 'OVERPAID', label: 'Overpaid' },
  ];
  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
      {cards.map(c => {
        const style = PAYMENT_STATUS_STYLES[c.key];
        return (
          <div key={c.key} className={`rounded-lg border border-gray-200 p-4 ${style.bg}`}>
            <p className={`text-xs font-medium uppercase tracking-wide ${style.text}`}>{c.label}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{summary.counts[c.key] || 0}</p>
          </div>
        );
      })}
    </div>
  );
}