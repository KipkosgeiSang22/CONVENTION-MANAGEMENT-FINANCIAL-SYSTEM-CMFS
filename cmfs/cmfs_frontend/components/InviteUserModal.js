/**
 * FILE: cmfs/cmfs_frontend/components/InviteUserModal.js
 * ACTION: REPLACE (Phase 4 — fix)
 *
 * Modal for inviting a new user.
 * Dynamically shows only the roles the caller can invite.
 *
 * County / region dropdowns only ever appear for Super Admin, and only
 * when inviting a county_head (county dropdown) or regional_head (region
 * dropdown). Every other caller — national_head, regional_head, or
 * county_head inviting operational staff (budget_creator, finance_viewer,
 * gate_official) — sees no scope fields at all, because the backend
 * always inherits county_id / region_id from the caller for those
 * invites regardless of what the form sends.
 *
 * Props:
 *   callerRole   {string}   — role of the currently logged-in user
 *   counties     {Array}    — [{ id, name }] for county dropdown (from conventions API)
 *   regions      {Array}    — [{ id, name }] for region dropdown
 *   onClose      {Function} — close without saving
 *   onSuccess    {Function} — called with the new user_id after successful invite
 */

import { useState } from 'react';
import { inviteUser, getInvitableRoles, roleRequiresCounty, roleRequiresRegion, ROLE_LABELS } from '../lib/users';

export default function InviteUserModal({ callerRole, counties = [], regions = [], onClose, onSuccess }) {
  const invitableRoles = getInvitableRoles(callerRole);

  const [form, setForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    role: invitableRoles[0]?.value || '',
    county_id: '',
    region_id: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [setupUrl, setSetupUrl] = useState(null);   // set once the invite succeeds
  const [invitedEmail, setInvitedEmail] = useState('');
  const [copied, setCopied] = useState(false);

  function handleChange(e) {
    const { name, value } = e.target;
    if (name === 'role') {
      // Reset scope fields whenever the target role changes, so a stale
      // county/region picked for a previous role selection is never
      // silently submitted for the new one.
      setForm(f => ({ ...f, role: value, county_id: '', region_id: '' }));
    } else {
      setForm(f => ({ ...f, [name]: value }));
    }
    setError('');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');

    if (!form.full_name.trim()) return setError('Full name is required.');
    if (!form.email.trim())     return setError('Email is required.');
    if (!form.role)             return setError('Role is required.');

    const payload = {
      full_name: form.full_name.trim(),
      email:     form.email.trim().toLowerCase(),
      role:      form.role,
    };
    if (form.phone.trim())              payload.phone     = form.phone.trim();
    if (form.county_id)                 payload.county_id = Number(form.county_id);
    if (form.region_id)                 payload.region_id = Number(form.region_id);

    setSubmitting(true);
    const { ok, data, error: apiError } = await inviteUser(payload);
    setSubmitting(false);

    if (!ok) {
      setError(apiError || 'Failed to send invitation.');
      return;
    }

    // Refresh the user list / parent state in the background, but keep the
    // modal open so the admin can grab the setup link — invitation emails
    // silently fail to send when no domain is configured on Resend, so the
    // link is the only reliable way to get new users this URL.
    onSuccess(data.user_id);
    setInvitedEmail(payload.email);
    setSetupUrl(data.setup_url || null);
  }

  async function handleCopyLink() {
    if (!setupUrl) return;
    try {
      await navigator.clipboard.writeText(setupUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API unavailable — the link is still selectable/visible in the input.
    }
  }

  const needsCounty = roleRequiresCounty(form.role, callerRole);
  const needsRegion = roleRequiresRegion(form.role, callerRole);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Invite New User</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition text-xl font-light leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* Form OR success screen with the setup link */}
        {setupUrl ? (
          <div className="px-6 py-5 space-y-4">
            <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg px-4 py-3">
              Invitation created for <strong>{invitedEmail}</strong>.
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Setup link
              </label>
              <p className="text-xs text-gray-500 mb-2">
                If email delivery isn't set up, copy this link and share it with the
                user directly (WhatsApp, SMS, etc). It expires in 48 hours.
              </p>
              <div className="flex gap-2">
                <input
                  readOnly
                  value={setupUrl}
                  onFocus={e => e.target.select()}
                  className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-xs text-gray-600 bg-gray-50 focus:outline-none"
                />
                <button
                  type="button"
                  onClick={handleCopyLink}
                  className="shrink-0 border border-gray-300 rounded-lg px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition"
                >
                  {copied ? 'Copied ✓' : 'Copy'}
                </button>
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => {
                  // Invite another user without leaving the modal.
                  setSetupUrl(null);
                  setInvitedEmail('');
                  setCopied(false);
                  setForm({ full_name: '', email: '', phone: '', role: invitableRoles[0]?.value || '', county_id: '', region_id: '' });
                }}
                className="flex-1 border border-gray-300 text-gray-700 rounded-lg py-2 text-sm font-medium hover:bg-gray-50 transition"
              >
                Invite another
              </button>
              <button
                type="button"
                onClick={onClose}
                className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 transition"
              >
                Done
              </button>
            </div>
          </div>
        ) : (
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
              {error}
            </div>
          )}

          {/* Full Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Full Name <span className="text-red-500">*</span>
            </label>
            <input
              name="full_name"
              value={form.full_name}
              onChange={handleChange}
              placeholder="e.g. Jane Wanjiku"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="jane@example.com"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Phone (optional) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Phone <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              name="phone"
              value={form.phone}
              onChange={handleChange}
              placeholder="+254 700 000 000"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Role */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Role <span className="text-red-500">*</span>
            </label>
            {invitableRoles.length === 0 ? (
              <p className="text-sm text-gray-400 italic">Your role cannot invite any users.</p>
            ) : (
              <select
                name="role"
                value={form.role}
                onChange={handleChange}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                {invitableRoles.map(r => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            )}
          </div>

          {/* Region (Super Admin only, when inviting a regional_head) */}
          {needsRegion && regions.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Region <span className="text-red-500">*</span>
              </label>
              <select
                name="region_id"
                value={form.region_id}
                onChange={handleChange}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="">— Select region —</option>
                {regions.map(r => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            </div>
          )}

          {/* County (Super Admin only, when inviting a county_head) */}
          {needsCounty && counties.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                County <span className="text-red-500">*</span>
              </label>
              <select
                name="county_id"
                value={form.county_id}
                onChange={handleChange}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="">— Select county —</option>
                {counties.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-gray-300 text-gray-700 rounded-lg py-2 text-sm font-medium hover:bg-gray-50 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || invitableRoles.length === 0}
              className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {submitting ? 'Sending…' : 'Send Invitation'}
            </button>
          </div>
        </form>
        )}
      </div>
    </div>
  );
}