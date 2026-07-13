/**
 * FILE: cmfs/cmfs_frontend/pages/budget/outstanding.js
 * ACTION: CREATE (Phase 9)
 *
 * County Head (or above): outstanding (INCOMPLETE/NOT_PAID) delegates
 * for a unit, with Chase and Write-Off actions. Finance Viewer and
 * Budget Creator can view but the action buttons are hidden — write-off
 * in particular is deliberately restricted to heads, not Budget Creator,
 * since it's an irreversible financial decision.
 */
import { useEffect, useState } from 'react';
import Link from 'next/link';
import useAuth from '../../lib/useAuth';
import InactivityGuard from '../../components/InactivityGuard';
import { getMyUnits, getOutstandingPayments, chasePayment, writeOffDelegate, fmtKES } from '../../lib/budget';

const HEAD_ROLES = ['super_admin', 'national_head', 'regional_head', 'county_head'];

export default function OutstandingPaymentsPage() {
  const { user, loading: authLoading } = useAuth();
  const canAct = HEAD_ROLES.includes(user?.role);

  const [units, setUnits] = useState(null);
  const [selectedUnitId, setSelectedUnitId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [delegates, setDelegates] = useState([]);

  const [chasingId, setChasingId] = useState(null);
  const [writeOffTarget, setWriteOffTarget] = useState(null);

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
    refresh();
  }, [selectedUnitId]);

  async function refresh() {
    setError('');
    const res = await getOutstandingPayments(selectedUnitId);
    if (res.ok) setDelegates(res.data.delegates || []);
    else setError(res.data?.error || 'Failed to load outstanding payments.');
  }

  async function handleChase(delegate) {
    setChasingId(delegate.id);
    const res = await chasePayment(delegate.delegate_id);
    setChasingId(null);
    if (res.ok) refresh();
    else alert(res.data?.error || 'Could not queue a reminder.');
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
          <h1 className="text-xl font-bold text-gray-900">Outstanding Payments</h1>
          {!canAct && (
            <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
              Read-only
            </span>
          )}
        </div>

        <div className="max-w-5xl mx-auto px-6 py-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-4 text-sm">{error}</div>
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

          {selectedUnitId && (
            <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
                    <th className="px-4 py-2.5">Delegate</th>
                    <th className="px-4 py-2.5">Category</th>
                    <th className="px-4 py-2.5 text-right">Balance Owed</th>
                    <th className="px-4 py-2.5">Status</th>
                    {canAct && <th className="px-4 py-2.5 text-right">Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {delegates.map(d => (
                    <tr key={d.id} className="border-t border-gray-100">
                      <td className="px-4 py-2.5">
                        <p className="font-medium text-gray-900">{d.full_name}</p>
                        <p className="text-xs text-gray-400">{d.delegate_id} · {d.email}</p>
                      </td>
                      <td className="px-4 py-2.5 text-gray-500">{d.category}</td>
                      <td className="px-4 py-2.5 text-right font-medium text-red-600">{fmtKES(d.balance_owed)}</td>
                      <td className="px-4 py-2.5">
                        {d.chase_status === 'pending_chase' ? (
                          <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                            Pending Chase
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
                            {d.payment_status}
                          </span>
                        )}
                      </td>
                      {canAct && (
                        <td className="px-4 py-2.5 text-right">
                          <div className="flex items-center justify-end gap-3">
                            <button
                              onClick={() => handleChase(d)}
                              disabled={chasingId === d.id}
                              className="text-xs text-blue-600 hover:underline disabled:opacity-50"
                            >
                              {chasingId === d.id ? 'Queuing…' : 'Chase'}
                            </button>
                            <button
                              onClick={() => setWriteOffTarget(d)}
                              className="text-xs text-red-600 hover:underline"
                            >
                              Write Off
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                  {delegates.length === 0 && (
                    <tr>
                      <td colSpan={canAct ? 5 : 4} className="px-4 py-10 text-center text-gray-400">
                        No outstanding payments for this convention. 🎉
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {writeOffTarget && (
        <WriteOffModal
          delegate={writeOffTarget}
          onCancel={() => setWriteOffTarget(null)}
          onDone={() => { setWriteOffTarget(null); refresh(); }}
        />
      )}
    </InactivityGuard>
  );
}

function WriteOffModal({ delegate, onCancel, onDone }) {
  const [reason, setReason] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit() {
    if (!reason.trim()) { setError('Reason is required.'); return; }
    if (totpCode.length !== 6) { setError('Enter your 6-digit TOTP code.'); return; }
    setError('');
    setSubmitting(true);
    const res = await writeOffDelegate(delegate.delegate_id, reason.trim(), totpCode);
    setSubmitting(false);
    if (!res.ok) { setError(res.data?.error || 'Could not write off this balance.'); return; }
    onDone();
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
        <p className="text-3xl mb-2 text-center">⚠️</p>
        <h3 className="text-lg font-bold text-gray-900 mb-1 text-center">Write Off Balance</h3>
        <p className="text-sm text-gray-500 mb-1 text-center">{delegate.full_name} · {delegate.delegate_id}</p>
        <p className="text-sm text-red-600 font-medium mb-4 text-center">
          {fmtKES(delegate.balance_owed)} will be permanently written off.
        </p>

        <label className="block text-xs font-medium text-gray-500 mb-1">Reason (required)</label>
        <textarea
          value={reason}
          onChange={e => setReason(e.target.value)}
          rows={2}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-red-500"
          autoFocus
        />

        <label className="block text-xs font-medium text-gray-500 mb-1">Your TOTP code (required)</label>
        <input
          type="text"
          inputMode="numeric"
          maxLength={6}
          value={totpCode}
          onChange={e => setTotpCode(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-center tracking-widest mb-3 focus:outline-none focus:ring-2 focus:ring-red-500"
        />

        {error && <p className="text-xs text-red-600 mb-3">{error}</p>}

        <p className="text-xs text-gray-400 mb-4">This action is irreversible and cannot be undone.</p>

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            disabled={submitting}
            className="flex-1 border border-gray-300 text-gray-700 rounded-lg py-2.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1 bg-red-600 text-white rounded-lg py-2.5 text-sm font-semibold hover:bg-red-700 disabled:opacity-50"
          >
            {submitting ? 'Writing off…' : 'Confirm Write-Off'}
          </button>
        </div>
      </div>
    </div>
  );
}
