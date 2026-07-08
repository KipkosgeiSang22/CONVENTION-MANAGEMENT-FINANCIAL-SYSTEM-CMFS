/**
 * FILE: cmfs/cmfs_frontend/pages/users/index.js
 * ACTION: NEW (Phase 4)
 *
 * User management list page.
 * Visible to: super_admin, national_head, regional_head, county_head.
 *
 * Features:
 *  - Paginated list of users within the caller's scope
 *  - Status badge (Active / Pending Setup / Locked)
 *  - Role filter dropdown
 *  - Invite button → opens InviteUserModal
 *  - Invalidate Sessions button (Super Admin only)
 *  - Delete user button (Super Admin only)
 */

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { getUser, logout, refreshToken } from '../../lib/auth';
import { api } from '../../lib/api';
import { listUsers, invalidateSessions, deleteUser, ROLE_LABELS } from '../../lib/users';
import UserStatusBadge from '../../components/UserStatusBadge';
import InviteUserModal from '../../components/InviteUserModal';
import InactivityGuard from '../../components/InactivityGuard';

const HEAD_ROLES = ['super_admin', 'national_head', 'regional_head', 'county_head'];

export default function UsersPage() {
  const router = useRouter();
  const [user, setUser]             = useState(null);
  const [users, setUsers]           = useState([]);
  const [total, setTotal]           = useState(0);
  const [page, setPage]             = useState(1);
  const [roleFilter, setRoleFilter] = useState('');
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState('');
  const [actionError, setActionError] = useState('');
  const [actionMsg, setActionMsg]   = useState('');
  const [showInvite, setShowInvite] = useState(false);
  const [counties, setCounties]     = useState([]);
  const [regions, setRegions]       = useState([]);
  const [confirmDelete, setConfirmDelete] = useState(null); // user object to delete

  // ── Auth check ─────────────────────────────────────────────────────────────
  useEffect(() => {
    async function init() {
      let u = getUser();
      if (!u) {
        const ok = await refreshToken();
        if (!ok) { router.replace('/auth/login'); return; }
        const res = await api.get('/api/auth/me/');
        if (res.ok && res.data?.user) { u = res.data.user; }
        else { router.replace('/auth/login'); return; }
      }
      if (!HEAD_ROLES.includes(u.role)) {
        router.replace('/dashboard');
        return;
      }
      setUser(u);
    }
    init();
  }, []);

  // ── Load counties/regions for invite modal ─────────────────────────────────
  useEffect(() => {
    async function loadGeo() {
      const [cRes, rRes] = await Promise.all([
        api.get('/api/conventions/counties/'),
        api.get('/api/conventions/regions/'),
      ]);
      if (cRes.ok)  setCounties(cRes.data.counties  || []);
      if (rRes.ok)  setRegions(rRes.data.regions    || []);
    }
    loadGeo();
  }, []);

  // ── Load users ─────────────────────────────────────────────────────────────
  const loadUsers = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setActionError('');
    const filters = { page };
    if (roleFilter) filters.role = roleFilter;

    const { ok, data, error: apiErr } = await listUsers(filters);
    setLoading(false);
    if (!ok) { setError(apiErr); return; }
    setUsers(data.users || []);
    setTotal(data.total || 0);
  }, [user, page, roleFilter]);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  // ── Actions ────────────────────────────────────────────────────────────────
  async function handleInvalidate(targetUser) {
    setActionError('');
    setActionMsg('');
    const { ok, data, error: apiErr } = await invalidateSessions(targetUser.id);
    if (!ok) { setActionError(apiErr); return; }
    setActionMsg(data.message || 'Sessions invalidated.');
  }

  async function handleDelete() {
    if (!confirmDelete) return;
    setActionError('');
    setActionMsg('');
    const { ok, data, error: apiErr } = await deleteUser(confirmDelete.id);
    setConfirmDelete(null);
    if (!ok) { setActionError(apiErr); return; }
    setActionMsg(data.message || 'User deleted.');
    loadUsers();
  }

  function handleInviteSuccess() {
    setActionMsg('Invitation sent successfully.');
    loadUsers();
  }

  async function handleLogout() {
    await logout();
    router.replace('/auth/login');
  }

  // ── Render guards ──────────────────────────────────────────────────────────
  if (!user) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  );

  const isSuperAdmin = user.role === 'super_admin';
  const pageCount = Math.ceil(total / 50);

  return (
    <InactivityGuard>
      <div className="min-h-screen bg-gray-50">

        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Link href="/dashboard">
              <span className="text-xl font-bold text-gray-900 cursor-pointer">KSCF CMFS</span>
            </Link>
            <span className="text-gray-300">/</span>
            <span className="text-sm text-gray-500">Users</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-gray-700">{user.full_name}</p>
              <p className="text-xs text-gray-400 capitalize">{user.role.replace(/_/g, ' ')}</p>
            </div>
            <button onClick={handleLogout} className="text-sm text-red-600 hover:underline">
              Log Out
            </button>
          </div>
        </header>

        <main className="max-w-6xl mx-auto px-6 py-8">

          {/* Page title + invite button */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Users</h1>
              <p className="text-sm text-gray-400 mt-0.5">{total} user{total !== 1 ? 's' : ''} in your scope</p>
            </div>
            <button
              onClick={() => { setShowInvite(true); setActionMsg(''); setActionError(''); }}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition"
            >
              + Invite User
            </button>
          </div>

          {/* Feedback banners */}
          {actionMsg && (
            <div className="mb-4 bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg px-4 py-3">
              {actionMsg}
            </div>
          )}
          {actionError && (
            <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
              {actionError}
            </div>
          )}

          {/* Filters */}
          <div className="flex gap-3 mb-4">
            <select
              value={roleFilter}
              onChange={e => { setRoleFilter(e.target.value); setPage(1); }}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All roles</option>
              {Object.entries(ROLE_LABELS).map(([val, label]) => (
                <option key={val} value={val}>{label}</option>
              ))}
            </select>
          </div>

          {/* Table */}
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <div className="animate-spin rounded-full h-7 w-7 border-b-2 border-blue-600" />
              </div>
            ) : error ? (
              <div className="text-center py-20 text-red-500 text-sm">{error}</div>
            ) : users.length === 0 ? (
              <div className="text-center py-20 text-gray-400">
                <p className="text-3xl mb-2">👤</p>
                <p>No users found{roleFilter ? ' for this role filter' : ''}.</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50">
                    <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Name</th>
                    <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3 hidden sm:table-cell">Email</th>
                    <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Role</th>
                    <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Status</th>
                    <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3 hidden md:table-cell">Last Login</th>
                    {isSuperAdmin && (
                      <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Actions</th>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {users.map(u => (
                    <tr key={u.id} className="hover:bg-gray-50 transition">
                      <td className="px-5 py-3 font-medium text-gray-900 whitespace-nowrap">{u.full_name}</td>
                      <td className="px-5 py-3 text-gray-500 hidden sm:table-cell">{u.email}</td>
                      <td className="px-5 py-3 text-gray-600 capitalize whitespace-nowrap">
                        {ROLE_LABELS[u.role] || u.role}
                      </td>
                      <td className="px-5 py-3">
                        <UserStatusBadge status={u.status} />
                      </td>
                      <td className="px-5 py-3 text-gray-400 text-xs hidden md:table-cell">
                        {u.last_login_at
                          ? new Date(u.last_login_at).toLocaleString('en-KE', { dateStyle: 'medium', timeStyle: 'short' })
                          : '—'}
                      </td>
                      {isSuperAdmin && (
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-3">
                            <button
                              onClick={() => handleInvalidate(u)}
                              className="text-xs text-amber-600 hover:underline whitespace-nowrap"
                            >
                              Invalidate Sessions
                            </button>
                            <button
                              onClick={() => { setConfirmDelete(u); setActionMsg(''); setActionError(''); }}
                              className="text-xs text-red-500 hover:underline"
                              disabled={u.id === user.id}
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination */}
          {pageCount > 1 && (
            <div className="flex items-center justify-between mt-4">
              <button
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
                className="text-sm text-gray-600 border border-gray-300 rounded-lg px-4 py-2 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                ← Previous
              </button>
              <span className="text-sm text-gray-400">Page {page} of {pageCount}</span>
              <button
                disabled={page >= pageCount}
                onClick={() => setPage(p => p + 1)}
                className="text-sm text-gray-600 border border-gray-300 rounded-lg px-4 py-2 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next →
              </button>
            </div>
          )}
        </main>
      </div>

      {/* Invite modal */}
      {showInvite && (
        <InviteUserModal
          callerRole={user.role}
          counties={counties}
          regions={regions}
          onClose={() => setShowInvite(false)}
          onSuccess={handleInviteSuccess}
        />
      )}

      {/* Delete confirmation modal */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 text-center">
            <p className="text-4xl mb-3">⚠️</p>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Delete user?</h3>
            <p className="text-sm text-gray-500 mb-6">
              This will permanently delete <strong>{confirmDelete.full_name}</strong> and cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmDelete(null)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-lg py-2 text-sm font-medium hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="flex-1 bg-red-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </InactivityGuard>
  );
}