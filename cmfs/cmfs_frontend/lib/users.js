/**
 * FILE: cmfs/cmfs_frontend/lib/users.js
 * ACTION: NEW (Phase 4)
 *
 * API helpers for all user management operations.
 * All functions return { ok, data, error } — never throw.
 */

import { api } from './api';

/**
 * List users visible to the caller.
 * @param {Object} filters - { role, county_id, region_id, page }
 */
export async function listUsers(filters = {}) {
  const params = new URLSearchParams();
  if (filters.role)       params.set('role', filters.role);
  if (filters.county_id)  params.set('county_id', filters.county_id);
  if (filters.region_id)  params.set('region_id', filters.region_id);
  if (filters.page)       params.set('page', filters.page);

  const qs = params.toString();
  const res = await api.get(`/api/users/${qs ? '?' + qs : ''}`);
  if (!res.ok) {
    return { ok: false, data: null, error: res.data?.error || 'Failed to load users.' };
  }
  return { ok: true, data: res.data, error: null };
}

/**
 * Invite a new user.
 * @param {Object} payload - { full_name, email, phone?, role, county_id?, region_id? }
 *   county_id / region_id are only ever meaningful when the caller is Super
 *   Admin inviting a county_head or regional_head. For every other
 *   caller/role combination the backend ignores whatever is sent here and
 *   inherits scope from the caller instead, so the form should simply omit
 *   these fields.
 */
export async function inviteUser(payload) {
  const res = await api.post('/api/users/invite/', payload);
  if (!res.ok) {
    return { ok: false, data: null, error: res.data?.error || 'Failed to send invitation.' };
  }
  return { ok: true, data: res.data, error: null };
}

/**
 * Update non-sensitive fields on a user (Super Admin only).
 * @param {number} userId
 * @param {Object} fields - subset of { full_name, phone, role, county_id, region_id }
 */
export async function patchUser(userId, fields) {
  const res = await api.patch(`/api/users/${userId}/`, fields);
  if (!res.ok) {
    return { ok: false, data: null, error: res.data?.error || 'Failed to update user.' };
  }
  return { ok: true, data: res.data, error: null };
}

/**
 * Hard-delete a user (Super Admin only).
 * @param {number} userId
 */
export async function deleteUser(userId) {
  const res = await api.del(`/api/users/${userId}/delete/`);
  if (!res.ok) {
    return { ok: false, data: null, error: res.data?.error || 'Failed to delete user.' };
  }
  return { ok: true, data: res.data, error: null };
}

/**
 * Invalidate all active sessions for a user (Super Admin only).
 * @param {number} userId
 */
export async function invalidateSessions(userId) {
  const res = await api.post(`/api/users/${userId}/invalidate-sessions/`, {});
  if (!res.ok) {
    return { ok: false, data: null, error: res.data?.error || 'Failed to invalidate sessions.' };
  }
  return { ok: true, data: res.data, error: null };
}

/**
 * Force-reset a user's TOTP (Super Admin only). Wipes their existing
 * authenticator + recovery codes and queues a fresh setup-link email.
 * Requires the *calling* Super Admin's own current TOTP code, since this
 * is a destructive action on someone else's account.
 * @param {number} userId
 * @param {string} totpCode - the Super Admin's own 6-digit TOTP code
 */
export async function resetUserTotp(userId, totpCode) {
  const res = await api.post('/api/auth/totp/admin-reset/', { user_id: userId, totp_code: totpCode });
  if (!res.ok) {
    return { ok: false, data: null, error: res.data?.error || 'Failed to reset TOTP.' };
  }
  return { ok: true, data: res.data, error: null };
}

// ── Role metadata ──────────────────────────────────────────────────────────────

/** Human-readable label for each backend role value. */
export const ROLE_LABELS = {
  super_admin:    'Super Admin',
  national_head:  'National Head',
  regional_head:  'Regional Head',
  county_head:    'County Head',
  budget_creator: 'Budget Creator',
  finance_viewer: 'Finance Viewer',
  gate_official:  'Gate Official',
  delegate:       'Delegate',
};

/**
 * Returns the roles a given caller role is allowed to invite.
 * Mirrors the backend _INVITE_HIERARCHY so the invite form
 * only shows valid options without an extra round-trip.
 *
 * Super Admin is the only one who creates head roles.
 * All three head roles invite the same operational staff within their own scope.
 */
const INVITE_HIERARCHY = {
  super_admin:   ['national_head', 'regional_head', 'county_head'],
  national_head: ['budget_creator', 'finance_viewer', 'gate_official'],
  regional_head: ['budget_creator', 'finance_viewer', 'gate_official'],
  county_head:   ['budget_creator', 'finance_viewer', 'gate_official'],
};

export function getInvitableRoles(callerRole) {
  return (INVITE_HIERARCHY[callerRole] || []).map(role => ({
    value: role,
    label: ROLE_LABELS[role] || role,
  }));
}

/**
 * Returns true if the invite form should show a county dropdown.
 *
 * Only Super Admin ever picks a county explicitly — when creating a
 * county_head. Every other caller (national_head, regional_head,
 * county_head) is inviting operational staff whose county_id is always
 * inherited automatically from the caller on the backend, so no field
 * is shown for them.
 */
export function roleRequiresCounty(targetRole, callerRole) {
  return callerRole === 'super_admin' && targetRole === 'county_head';
}

/**
 * Returns true if the invite form should show a region dropdown.
 *
 * Only Super Admin ever picks a region explicitly — when creating a
 * regional_head. Operational staff invited by any head role always
 * inherit region_id from the caller on the backend (and it's null
 * entirely for a regional convention's county_id — region_id is the
 * real scope anchor there), so no field is shown for them.
 */
export function roleRequiresRegion(targetRole, callerRole) {
  return callerRole === 'super_admin' && targetRole === 'regional_head';
}