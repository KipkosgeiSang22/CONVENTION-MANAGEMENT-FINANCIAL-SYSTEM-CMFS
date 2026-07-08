/**
 * FILE: cmfs/cmfs_frontend/pages/register/index.js
 * ACTION: CREATE (Phase 6)
 *
 * Public self-registration form. NOT wrapped in useAuth/InactivityGuard —
 * this page must work for a parent/delegate with no CMFS account at all.
 */

import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import {
  getRegistrationOptions, publicRegister, CATEGORY_LABELS, firstErrorMessage,
} from '../../lib/delegates';

const CATEGORIES = Object.entries(CATEGORY_LABELS).map(([value, label]) => ({ value, label }));

export default function PublicRegisterPage() {
  const router = useRouter();
  const [options, setOptions] = useState(null);
  const [loadingOptions, setLoadingOptions] = useState(true);

  const [form, setForm] = useState({
    full_name: '', email: '', category: '', county_id: '',
    parent_name: '', parent_phone: '', accept_terms: false,
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [banner, setBanner] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      const res = await getRegistrationOptions();
      if (res.ok) setOptions(res.data.options || []);
      setLoadingOptions(false);
    })();
  }, []);

  function set(field, value) {
    setForm(f => ({ ...f, [field]: value }));
    setFieldErrors(e => ({ ...e, [field]: undefined }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setBanner('');
    setFieldErrors({});
    setSubmitting(true);

    const res = await publicRegister({
      ...form,
      county_id: Number(form.county_id),
    });

    setSubmitting(false);

    if (res.ok) {
      router.push(`/register/status/${res.data.registration_id}?amount=${res.data.amount_due}`);
      return;
    }

    if (res.status === 429) {
      setBanner('Too many attempts from this connection. Please wait a minute and try again.');
      return;
    }

    if (res.data?.code === 'validation_error' && typeof res.data.error === 'object') {
      setFieldErrors(res.data.error);
      return;
    }

    setBanner(firstErrorMessage(res.data, 'Registration failed. Please check your details and try again.'));
  }

  const err = (field) => fieldErrors[field]?.[0];

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-lg mx-auto">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Convention Registration</h1>
          <p className="text-gray-500 text-sm mt-1">Register a delegate for the upcoming convention.</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
          {banner && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">{banner}</div>
          )}

          <Field label="Delegate Full Name" error={err('full_name')}>
            <input required value={form.full_name} onChange={e => set('full_name', e.target.value)}
              className="input" placeholder="e.g. Jane Wanjiru" />
          </Field>

          <Field label="Delegate Email" error={err('email')}>
            <input required type="email" value={form.email} onChange={e => set('email', e.target.value)}
              className="input" placeholder="jane@example.com" />
          </Field>

          <Field label="Category" error={err('category')}>
            <select required value={form.category} onChange={e => set('category', e.target.value)} className="input">
              <option value="" disabled>Select category…</option>
              {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </Field>

          <Field label="County" error={err('county_id')}>
            {loadingOptions ? (
              <p className="text-sm text-gray-400">Loading counties…</p>
            ) : options && options.length > 0 ? (
              <select required value={form.county_id} onChange={e => set('county_id', e.target.value)} className="input">
                <option value="" disabled>Select county…</option>
                {options.map(o => (
                  <option key={o.county_id} value={o.county_id}>{o.county_name} — {o.convention_name}</option>
                ))}
              </select>
            ) : (
              <p className="text-sm text-amber-600">Registration is not currently open for any county. Please check back later.</p>
            )}
          </Field>

          <Field label="Parent/Guardian Name" error={err('parent_name')}>
            <input required value={form.parent_name} onChange={e => set('parent_name', e.target.value)}
              className="input" placeholder="e.g. John Wanjiru" />
          </Field>

          <Field label="Parent/Guardian Phone (M-Pesa)" error={err('parent_phone')}>
            <input required value={form.parent_phone} onChange={e => set('parent_phone', e.target.value)}
              className="input" placeholder="07XXXXXXXX" />
          </Field>

          <label className="flex items-start gap-2 text-sm text-gray-600">
            <input type="checkbox" checked={form.accept_terms}
              onChange={e => set('accept_terms', e.target.checked)}
              className="mt-1" />
            <span>I accept the Terms &amp; Conditions of the convention.</span>
          </label>
          {err('accept_terms') && <p className="text-xs text-red-600">{err('accept_terms')}</p>}

          <button type="submit" disabled={submitting || (options && options.length === 0)}
            className="w-full bg-blue-600 text-white rounded-lg py-2.5 font-medium hover:bg-blue-700 disabled:opacity-50">
            {submitting ? 'Submitting…' : 'Register & Pay'}
          </button>
        </form>
      </div>

      <style jsx>{`
        .input {
          width: 100%;
          border: 1px solid #d1d5db;
          border-radius: 0.5rem;
          padding: 0.5rem 0.75rem;
          font-size: 0.875rem;
        }
      `}</style>
    </div>
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