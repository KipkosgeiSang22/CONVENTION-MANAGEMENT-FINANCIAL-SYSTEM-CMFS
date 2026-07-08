/**
 * FILE: cmfs/cmfs_frontend/pages/delegates/manual.js
 * ACTION: CREATE (Phase 6)
 *
 * Budget Creator (or above) registers a delegate in person — e.g. a
 * parent walks in with cash, or wants staff to trigger the M-Pesa
 * prompt on their behalf.
 */

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import useAuth from '../../lib/useAuth';
import InactivityGuard from '../../components/InactivityGuard';
import { manualRegister, CATEGORY_LABELS, firstErrorMessage, getRegistrationStatus } from '../../lib/delegates';
import { listCounties } from '../../lib/conventions';

const CATEGORIES = Object.entries(CATEGORY_LABELS).map(([value, label]) => ({ value, label }));
const EDIT_ROLES = ['budget_creator', 'super_admin', 'national_head', 'regional_head', 'county_head'];
const POLL_MS = 4000;

export default function ManualRegistrationPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [countyName, setCountyName] = useState('');
  const [form, setForm] = useState({
    full_name: '', email: '', category: '', parent_name: '', parent_phone: '',
    accept_terms: false, payment_method: 'cash', amount_received_now: '',
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [banner, setBanner] = useState('');
  const [success, setSuccess] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  // Live payment status while an M-Pesa payment is still resolving.
  // Cash payments confirm synchronously on submit and never need this.
  const [pollStatus, setPollStatus] = useState(null); // { registration_status, delegate_id, payment_status }
  const pollTimerRef = useRef(null);

  useEffect(() => {
    return () => clearTimeout(pollTimerRef.current);
  }, []);

  async function pollDelegateStatus(delegatePk) {
    const res = await getRegistrationStatus(delegatePk);
    if (!res.ok) return; // transient network hiccup — next tick will retry
    setPollStatus(res.data);

    const settled = res.data.registration_status !== 'pending' ||
      ['failed', 'timeout'].includes(res.data.payment_status);

    if (!settled) {
      pollTimerRef.current = setTimeout(() => pollDelegateStatus(delegatePk), POLL_MS);
    }
  }

  useEffect(() => {
    if (!user?.county_id) return;
    (async () => {
      const res = await listCounties();
      if (res.ok) {
        const county = (res.data.counties || res.data || []).find(c => c.id === user.county_id);
        if (county) setCountyName(county.name);
      }
    })();
  }, [user]);

  function set(field, value) {
    setForm(f => ({ ...f, [field]: value }));
    setFieldErrors(e => ({ ...e, [field]: undefined }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setBanner('');
    setFieldErrors({});
    setSubmitting(true);

    const res = await manualRegister({
      ...form,
      county_id: user.county_id,
      amount_received_now: Number(form.amount_received_now),
    });

    setSubmitting(false);

    if (res.ok) {
      setSuccess(res.data.delegate);
      if (form.payment_method === 'mpesa') {
        setPollStatus({
          registration_status: res.data.delegate.registration_status,
          delegate_id: res.data.delegate.delegate_id,
          payment_status: 'initiated',
        });
        pollDelegateStatus(res.data.delegate.id);
      }
      return;
    }
    if (res.data?.code === 'validation_error' && typeof res.data.error === 'object') {
      setFieldErrors(res.data.error);
      return;
    }
    setBanner(firstErrorMessage(res.data, 'Registration failed. Please check the details and try again.'));
  }

  if (authLoading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!EDIT_ROLES.includes(user.role)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 text-gray-500">
        You don't have access to manual registration.
      </div>
    );
  }

  const err = (field) => fieldErrors[field]?.[0];

  return (
    <InactivityGuard>
      <div className="min-h-screen bg-gray-50">
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-3">
          <Link href="/delegates" className="text-gray-400 hover:text-gray-600 text-sm">← Delegates</Link>
          <span className="text-gray-300">/</span>
          <h1 className="text-xl font-bold text-gray-900">Manual Registration</h1>
        </div>

        <div className="max-w-lg mx-auto px-6 py-8">
          {success ? (
            <div className="bg-white border border-green-200 rounded-lg p-6 text-center">
              <div className="text-5xl mb-3">✅</div>
              <h2 className="text-lg font-bold text-gray-900 mb-1">Delegate Registered</h2>
              {success.delegate_id ? (
                <p className="text-gray-600 text-sm mb-4">
                  Delegate ID: <span className="font-mono font-semibold">{success.delegate_id}</span>
                </p>
              ) : pollStatus ? (
                pollStatus.registration_status === 'active' ? (
                  <p className="text-green-700 text-sm mb-4">
                    Payment confirmed. Delegate ID:{' '}
                    <span className="font-mono font-semibold">{pollStatus.delegate_id}</span>
                  </p>
                ) : ['failed', 'timeout'].includes(pollStatus.payment_status) ? (
                  <p className="text-red-600 text-sm mb-4">
                    The M-Pesa payment {pollStatus.payment_status === 'timeout' ? 'timed out' : 'failed or was cancelled'}.
                    Use the delegates list to retry the payment for this delegate.
                  </p>
                ) : (
                  <p className="text-gray-600 text-sm mb-4 flex items-center justify-center gap-2">
                    <span className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-blue-600 inline-block" />
                    Waiting for M-Pesa confirmation on the parent/guardian's phone…
                  </p>
                )
              ) : (
                <p className="text-gray-600 text-sm mb-4">M-Pesa prompt sent — Delegate ID will be generated once payment confirms.</p>
              )}
              <button onClick={() => {
                  clearTimeout(pollTimerRef.current);
                  setPollStatus(null);
                  setSuccess(null);
                  setForm({ ...form, full_name: '', email: '', parent_name: '', parent_phone: '', amount_received_now: '', accept_terms: false });
                }}
                className="text-sm text-blue-600 hover:underline">
                Register another delegate
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
              {banner && (
                <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">{banner}</div>
              )}

              <p className="text-xs text-gray-400 uppercase tracking-wide">
                Registering for: <span className="font-medium text-gray-600">{countyName || `County #${user.county_id}`}</span>
              </p>

              <Field label="Delegate Full Name" error={err('full_name')}>
                <input required value={form.full_name} onChange={e => set('full_name', e.target.value)} className="input" />
              </Field>

              <Field label="Delegate Email" error={err('email')}>
                <input required type="email" value={form.email} onChange={e => set('email', e.target.value)} className="input" />
              </Field>

              <Field label="Category" error={err('category')}>
                <select required value={form.category} onChange={e => set('category', e.target.value)} className="input">
                  <option value="" disabled>Select category…</option>
                  {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
              </Field>

              <Field label="Parent/Guardian Name" error={err('parent_name')}>
                <input required value={form.parent_name} onChange={e => set('parent_name', e.target.value)} className="input" />
              </Field>

              <Field label="Parent/Guardian Phone" error={err('parent_phone')}>
                <input required value={form.parent_phone} onChange={e => set('parent_phone', e.target.value)} className="input" placeholder="07XXXXXXXX" />
              </Field>

              <div className="grid grid-cols-2 gap-3">
                <Field label="Payment Method">
                  <select value={form.payment_method} onChange={e => set('payment_method', e.target.value)} className="input">
                    <option value="cash">Cash</option>
                    <option value="mpesa">M-Pesa</option>
                  </select>
                </Field>
                <Field label="Amount Received Now" error={err('amount_received_now')}>
                  <input required type="number" min="0" step="0.01" value={form.amount_received_now}
                    onChange={e => set('amount_received_now', e.target.value)} className="input" placeholder="KES" />
                </Field>
              </div>

              <label className="flex items-start gap-2 text-sm text-gray-600">
                <input type="checkbox" checked={form.accept_terms} onChange={e => set('accept_terms', e.target.checked)} className="mt-1" />
                <span>Parent/Guardian has accepted the Terms &amp; Conditions.</span>
              </label>
              {err('accept_terms') && <p className="text-xs text-red-600">{err('accept_terms')}</p>}

              <button type="submit" disabled={submitting}
                className="w-full bg-blue-600 text-white rounded-lg py-2.5 font-medium hover:bg-blue-700 disabled:opacity-50">
                {submitting ? 'Submitting…' : 'Register Delegate'}
              </button>
            </form>
          )}
        </div>
      </div>

      <style jsx global>{`
        .input {
          width: 100%;
          border: 1px solid #d1d5db;
          border-radius: 0.5rem;
          padding: 0.5rem 0.75rem;
          font-size: 0.875rem;
        }
      `}</style>
    </InactivityGuard>
  );
}

function Field({ label, error, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
    </div>
  );
}