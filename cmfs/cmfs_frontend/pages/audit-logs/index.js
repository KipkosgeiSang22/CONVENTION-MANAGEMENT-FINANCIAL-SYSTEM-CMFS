/**
 * FILE: cmfs/cmfs_frontend/pages/audit-logs/index.js
 * ACTION: CREATE (Phase 11)
 *
 * Audit log viewer. Visible to: super_admin only.
 * Filterable by user, action (substring match), and date range; paginated.
 */

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { getUser, logout, refreshToken } from '../../lib/auth';
import { api } from '../../lib/api';
import { listAuditLogs } from '../../lib/auditLogs';
import InactivityGuard from '../../components/InactivityGuard';

const PAGE_SIZE = 50;

export default function AuditLogsPage() {
  const router = useRouter();
  const [user, setUser] = useState(null);

  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [userIdFilter, setUserIdFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // ── Auth check ───────────────────────────────────────────────────────────
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
      if (u.role !== 'super_admin') {
        router.replace('/dashboard');
        return;
      }
      setUser(u);
    }
    init();
  }, []);

  // ── Load logs ────────────────────────────────────────────────────────────
  const loadLogs = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError('');
    const filters = { page, page_size: PAGE_SIZE };
    if (userIdFilter) filters.user_id = userIdFilter;
    if (actionFilter) filters.action = actionFilter;
    if (dateFrom) filters.date_from = dateFrom;
    if (dateTo) filters.date_to = dateTo;

    const res = await listAuditLogs(filters);
    setLoading(false);
    if (!res.ok) { setError(res.data?.error || 'Could not load audit logs.'); return; }
    setLogs(res.data.results || []);
    setTotal(res.data.total || 0);
  }, [user, page, userIdFilter, actionFilter, dateFrom, dateTo]);

  useEffect(() => { loadLogs(); }, [loadLogs]);

  function applyFilters(e) {
    e.preventDefault();
    setPage(1);
    loadLogs();
  }

  function clearFilters() {
    setUserIdFilter(''); setActionFilter(''); setDateFrom(''); setDateTo(''); setPage(1);
  }

  async function handleLogout() {
    await logout();
    router.replace('/auth/login');
  }

  if (!user) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  );

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <InactivityGuard>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Link href="/dashboard" className="text-xl font-bold text-gray-900 hover:text-blue-600">KSCF CMFS</Link>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm font-medium text-gray-700">{user.full_name}</p>
              <p className="text-xs text-gray-400 capitalize">{user.role.replace(/_/g, ' ')}</p>
            </div>
            <button onClick={handleLogout} className="text-sm text-red-600 hover:underline">Log Out</button>
          </div>
        </header>

        <main className="max-w-6xl mx-auto px-6 py-8">
          <div className="flex items-center gap-2 text-sm text-gray-400 mb-4">
            <Link href="/dashboard" className="hover:text-blue-600">Dashboard</Link>
            <span>/</span>
            <span className="text-gray-700">Audit Log</span>
          </div>

          <h1 className="text-2xl font-bold text-gray-900 mb-1">Audit Log</h1>
          <p className="text-sm text-gray-500 mb-6">Every recorded system action — logins, edits, closures, and admin actions.</p>

          <form onSubmit={applyFilters} className="bg-white border border-gray-200 rounded-lg p-4 mb-5 flex flex-wrap gap-3 items-end">
            <div>
              <label className="block text-xs text-gray-500 mb-1">User ID</label>
              <input value={userIdFilter} onChange={e => setUserIdFilter(e.target.value)}
                placeholder="e.g. 42" className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-28" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Action contains</label>
              <input value={actionFilter} onChange={e => setActionFilter(e.target.value)}
                placeholder="e.g. financially_closed" className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-56" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">From</label>
              <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">To</label>
              <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm" />
            </div>
            <button type="submit" className="bg-blue-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-blue-700">
              Apply Filters
            </button>
            <button type="button" onClick={clearFilters} className="text-sm text-gray-500 hover:underline">
              Clear
            </button>
          </form>

          {error && <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm mb-4">{error}</div>}

          <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
            {loading ? (
              <div className="p-8 flex justify-center">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
              </div>
            ) : logs.length === 0 ? (
              <div className="p-8 text-center text-gray-400 text-sm">No matching audit events.</div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-400 uppercase border-b border-gray-100">
                    <th className="py-2 px-4">Timestamp</th>
                    <th className="py-2 px-4">User</th>
                    <th className="py-2 px-4">Action</th>
                    <th className="py-2 px-4">Table / Record</th>
                    <th className="py-2 px-4">IP</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map(log => (
                    <tr key={log.id} className="border-b border-gray-50 align-top">
                      <td className="py-2 px-4 text-gray-500 whitespace-nowrap">
                        {new Date(log.timestamp).toLocaleString('en-KE')}
                      </td>
                      <td className="py-2 px-4 text-gray-700">{log.user_name || `#${log.user_id ?? '—'}`}</td>
                      <td className="py-2 px-4 text-gray-700 font-mono text-xs">{log.action}</td>
                      <td className="py-2 px-4 text-gray-500">
                        {log.table_name ? `${log.table_name}${log.record_id ? ` #${log.record_id}` : ''}` : '—'}
                      </td>
                      <td className="py-2 px-4 text-gray-400">{log.ip_address || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {totalPages > 1 && (
            <div className="flex justify-between items-center mt-4 text-sm">
              <p className="text-gray-400">Page {page} of {totalPages} — {total} events</p>
              <div className="flex gap-2">
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
                  className="border border-gray-300 rounded-lg px-3 py-1.5 disabled:opacity-40 hover:bg-gray-50">← Prev</button>
                <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                  className="border border-gray-300 rounded-lg px-3 py-1.5 disabled:opacity-40 hover:bg-gray-50">Next →</button>
              </div>
            </div>
          )}
        </main>
      </div>
    </InactivityGuard>
  );
}
