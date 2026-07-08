
/*TODO Restrict close to super_admin only (simplest fix — they coordinate confirmation from all county heads first)*/
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import useAuth from '../../lib/useAuth';
import {
  getConvention, publishConvention, activateConvention, endConvention,
  closeConventionFinancially, archiveConvention, triggerOpeningDayReports,
  STATUS_LABELS, STATUS_COLORS, getAvailableTransitions,
} from '../../lib/conventions';

export default function ConventionDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  const { user, loading: authLoading } = useAuth();

  const [convention, setConvention] = useState(null);
  const [loadingConv, setLoadingConv] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Modals
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [closeStep, setCloseStep] = useState('checklist');
  const [checklist, setChecklist] = useState({
    expensesEntered: false, outstandingResolved: false,
    postConventionEntered: false, offeringConfirmed: false,
  });
  const [totpCode, setTotpCode] = useState('');

  useEffect(() => {
    if (id && user) fetchConvention();
  }, [id, user]);

  async function fetchConvention() {
    setLoadingConv(true);
    try {
      const res = await getConvention(id);
      if (!res.ok) throw new Error(res.data?.error || 'Convention not found.');
      setConvention(res.data.convention);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingConv(false);
    }
  }

  async function handleAction(action) {
    setError(''); setSuccessMsg(''); setActionLoading(true);
    try {
      let res;
      if (action === 'publish') res = await publishConvention(id);
      else if (action === 'activate') res = await activateConvention(id);
      else if (action === 'end') res = await endConvention(id);
      else if (action === 'archive') res = await archiveConvention(id);
      else if (action === 'opening_reports') res = await triggerOpeningDayReports(id);
      else return;
      if (!res.ok) throw new Error(res.data?.error || 'Action failed.');
      setSuccessMsg(res.data.message || 'Done.');
      if (res.data.convention) setConvention(res.data.convention);
      else await fetchConvention();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleFinancialClose() {
    setError('');
    if (totpCode.length !== 6) { setError('Enter your 6-digit TOTP code.'); return; }
    setActionLoading(true);
    try {
      const res = await closeConventionFinancially(id, totpCode);
      if (!res.ok) throw new Error(res.data?.error || 'Close failed.');
      setShowCloseModal(false);
      setSuccessMsg(res.data.message || 'Convention financially closed.');
      if (res.data.convention) setConvention(res.data.convention);
      else await fetchConvention();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  if (authLoading || !user) return <Spinner />;
  if (loadingConv) return <Spinner />;
  if (!convention) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <p className="text-red-600 mb-4">{error || 'Convention not found.'}</p>
        <Link href="/conventions" className="text-blue-600 hover:underline text-sm">← Back</Link>
      </div>
    </div>
  );

  const transitions = getAvailableTransitions(convention, user.role);
  const statusClass = STATUS_COLORS[convention.status] || 'bg-gray-100 text-gray-700';
  const checklistDone = Object.values(checklist).every(Boolean);

  const btnClass = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    success: 'bg-green-600 text-white hover:bg-green-700',
    warning: 'bg-yellow-500 text-white hover:bg-yellow-600',
    danger: 'bg-red-600 text-white hover:bg-red-700',
    info: 'bg-indigo-600 text-white hover:bg-indigo-700',
    secondary: 'border border-gray-300 text-gray-700 hover:bg-gray-50',
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
          <Link href="/dashboard" className="hover:text-blue-600">Dashboard</Link>
          <span>/</span>
          <Link href="/conventions" className="hover:text-blue-600">Conventions</Link>
          <span>/</span>
          <span className="text-gray-700">{convention.name}</span>
        </div>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold text-gray-900">{convention.name}</h1>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusClass}`}>
                {STATUS_LABELS[convention.status]}
              </span>
              <span className="text-sm bg-gray-100 text-gray-600 px-2 py-0.5 rounded capitalize">{convention.scope}</span>
            </div>
            <p className="text-gray-500 text-sm mt-1">{convention.start_date} → {convention.end_date}</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-6 space-y-5">
        {successMsg && <div className="bg-green-50 border border-green-200 text-green-700 rounded-lg px-4 py-3 text-sm">✓ {successMsg}</div>}
        {error && <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">{error}</div>}

        {/* Actions */}
        {transitions.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-lg p-5">
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Available Actions</h2>
            <div className="flex flex-wrap gap-3">
              {transitions.map(t => (
                <button key={t.action} disabled={actionLoading}
                  onClick={() => {
                    if (t.action === 'publish') { setShowPublishModal(true); return; }
                    if (t.action === 'close') { setShowCloseModal(true); setCloseStep('checklist'); return; }
                    handleAction(t.action);
                  }}
                  className={`px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 transition ${btnClass[t.variant] || btnClass.secondary}`}>
                  {actionLoading ? '…' : t.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Details grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="bg-white border border-gray-200 rounded-lg p-5">
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-4">Details</h2>
            <dl className="space-y-2 text-sm">
              {[
                ['Start Date', convention.start_date],
                ['End Date', convention.end_date],
                ['Registration', convention.is_registration_open ? '✓ Open' : '✗ Closed'],
                ['Scope Locked', convention.scope_locked ? '✓ Yes' : '✗ No (Draft)'],
              ].map(([l, v]) => (
                <div key={l} className="flex justify-between">
                  <dt className="text-gray-500">{l}</dt>
                  <dd className="font-medium text-gray-900">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-5">
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-4">Registration Fees</h2>
            <dl className="space-y-2 text-sm">
              {[
                ['Student', `KES ${Number(convention.fee_student).toLocaleString()}`],
                ['Kessat', `KES ${Number(convention.fee_kessat).toLocaleString()}`],
                ['Associate', `KES ${Number(convention.fee_associate).toLocaleString()}`],
              ].map(([l, v]) => (
                <div key={l} className="flex justify-between">
                  <dt className="text-gray-500">{l}</dt>
                  <dd className="font-medium text-gray-900">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>

        {/* Units */}
        {convention.units?.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-lg p-5">
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-4">
              Convention Units ({convention.units.length})
            </h2>
            <div className="divide-y divide-gray-100">
              {convention.units.map(u => (
                <div key={u.id} className="py-3 flex justify-between items-center">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{u.display_name || `Unit ${u.id}`}</p>
                    <p className="text-xs text-gray-400 capitalize">{u.scope_type}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {convention.description && (
          <div className="bg-white border border-gray-200 rounded-lg p-5">
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Description</h2>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{convention.description}</p>
          </div>
        )}
      </div>

      {/* Publish modal */}
      {showPublishModal && (
        <Modal onClose={() => setShowPublishModal(false)}>
          <h3 className="text-lg font-bold text-gray-900 mb-3">⚠️ Publish Convention</h3>
          <p className="text-sm text-gray-600 mb-3">Publishing <strong>{convention.name}</strong> will:</p>
          <ul className="text-sm text-gray-700 list-disc pl-5 space-y-1 mb-4">
            <li>Open delegate registration</li>
            <li><strong>Permanently lock</strong> scope, fees and unit structure</li>
            <li>Email all assigned heads</li>
          </ul>
          <p className="text-sm text-red-600 font-semibold mb-5">This cannot be undone.</p>
          <div className="flex gap-3 justify-end">
            <button onClick={() => setShowPublishModal(false)}
              className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm hover:bg-gray-50">Cancel</button>
            <button onClick={() => { setShowPublishModal(false); handleAction('publish'); }}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
              Confirm Publish
            </button>
          </div>
        </Modal>
      )}

      {/* Financial close modal */}
      {showCloseModal && (
        <Modal onClose={() => setShowCloseModal(false)}>
          {closeStep === 'checklist' ? (
            <>
              <h3 className="text-lg font-bold text-gray-900 mb-3">Pre-Close Checklist</h3>
              <p className="text-sm text-gray-500 mb-4">Confirm all items before closing. This is <strong>irreversible</strong>.</p>
              <div className="space-y-3 mb-6">
                {[
                  ['expensesEntered', 'All expense vouchers have been entered'],
                  ['outstandingResolved', 'Outstanding payments resolved or written off'],
                  ['postConventionEntered', 'Post-convention expenses entered'],
                  ['offeringConfirmed', 'Offering and tithes confirmed'],
                ].map(([key, label]) => (
                  <label key={key} className="flex items-start gap-3 cursor-pointer">
                    <input type="checkbox" className="mt-0.5 accent-blue-600"
                      checked={checklist[key]}
                      onChange={e => setChecklist(p => ({ ...p, [key]: e.target.checked }))} />
                    <span className="text-sm text-gray-700">{label}</span>
                  </label>
                ))}
              </div>
              <div className="flex gap-3 justify-end">
                <button onClick={() => setShowCloseModal(false)}
                  className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm hover:bg-gray-50">Cancel</button>
                <button onClick={() => { setCloseStep('totp'); setError(''); }} disabled={!checklistDone}
                  className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-40">
                  Continue →
                </button>
              </div>
            </>
          ) : (
            <>
              <h3 className="text-lg font-bold text-gray-900 mb-3">🔐 Enter TOTP to Confirm</h3>
              <p className="text-sm text-gray-600 mb-5">
                Enter your Authenticator code to financially close <strong>{convention.name}</strong>.
                All data becomes <strong>read-only</strong>.
              </p>
              <input type="text" inputMode="numeric" maxLength={6} placeholder="000000"
                value={totpCode} onChange={e => setTotpCode(e.target.value.replace(/\D/g, ''))}
                className="w-full border border-gray-300 rounded-lg px-3 py-3 text-center tracking-widest text-2xl font-mono focus:outline-none focus:ring-2 focus:ring-red-500 mb-4" />
              {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
              <div className="flex gap-3 justify-end">
                <button onClick={() => setCloseStep('checklist')}
                  className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm hover:bg-gray-50">← Back</button>
                <button onClick={handleFinancialClose} disabled={actionLoading || totpCode.length !== 6}
                  className="bg-red-600 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-red-700 disabled:opacity-50">
                  {actionLoading ? 'Closing…' : 'Close Financially'}
                </button>
              </div>
            </>
          )}
        </Modal>
      )}
    </div>
  );
}

function Spinner() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  );
}

function Modal({ children, onClose }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 text-2xl leading-none">×</button>
        {children}
      </div>
    </div>
  );
}