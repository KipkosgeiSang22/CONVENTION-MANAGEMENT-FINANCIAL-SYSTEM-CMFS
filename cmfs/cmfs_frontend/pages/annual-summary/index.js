/**
 * FILE: cmfs/cmfs_frontend/pages/annual-summary/index.js
 * ACTION: CREATE (Phase 11)
 *
 * Lists every Annual Summary generated so far (one row per calendar year —
 * see reports.models.AnnualSummary), with download links, and a dev-only
 * "generate now" action for testing without waiting for the automatic
 * 7-days-after-December-close trigger.
 * Visible to: super_admin only.
 */

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { getUser, logout, refreshToken } from '../../lib/auth';
import { api } from '../../lib/api';
import { listAnnualSummaries, downloadAnnualSummary, devGenerateAnnualSummary } from '../../lib/reports';
import InactivityGuard from '../../components/InactivityGuard';

const STATUS_LABELS = { pending: 'Pending', generated: 'Generated', failed: 'Failed' };
const STATUS_CLASSES = {
  pending: 'bg-gray-100 text-gray-500',
  generated: 'bg-green-50 text-green-700',
  failed: 'bg-red-50 text-red-700',
};

export default function AnnualSummaryPage() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [summaries, setSummaries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [genYear, setGenYear] = useState(new Date().getFullYear());
  const [generating, setGenerating] = useState(false);
  const [msg, setMsg] = useState('');

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
      if (u.role !== 'super_admin') { router.replace('/dashboard'); return; }
      setUser(u);
    }
    init();
  }, []);

  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    const res = await listAnnualSummaries();
    setLoading(false);
    if (!res.ok) { setError(res.data?.error || 'Could not load annual summaries.'); return; }
    setSummaries(res.data.annual_summaries || []);
  }, [user]);

  useEffect(() => { load(); }, [load]);

  async function handleGenerate() {
    setGenerating(true); setError(''); setMsg('');
    const res = await devGenerateAnnualSummary(genYear);
    setGenerating(false);
    if (!res.ok) { setError(res.data?.error || 'Generation failed.'); return; }
    setMsg(res.data.message || 'Done.');
    await load();
  }

  async function handleDownload(year, format) {
    const res = await downloadAnnualSummary(year, format);
    if (!res.ok) setError(res.data?.error || 'Download failed.');
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

  return (
    <InactivityGuard>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
          <Link href="/dashboard" className="text-xl font-bold text-gray-900 hover:text-blue-600">KSCF CMFS</Link>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm font-medium text-gray-700">{user.full_name}</p>
              <p className="text-xs text-gray-400 capitalize">{user.role.replace(/_/g, ' ')}</p>
            </div>
            <button onClick={handleLogout} className="text-sm text-red-600 hover:underline">Log Out</button>
          </div>
        </header>

        <main className="max-w-4xl mx-auto px-6 py-8">
          <div className="flex items-center gap-2 text-sm text-gray-400 mb-4">
            <Link href="/dashboard" className="hover:text-blue-600">Dashboard</Link>
            <span>/</span>
            <span className="text-gray-700">Annual Summary</span>
          </div>

          <h1 className="text-2xl font-bold text-gray-900 mb-1">Annual Summary Reports</h1>
          <p className="text-sm text-gray-500 mb-6">
            Generated automatically 7 days after a December convention financially closes — aggregating every
            convention closed that year: delegate totals, income/expenditure, surplus/deficit per county,
            year-on-year comparison, top counties, collection efficiency, unbudgeted and written-off amounts.
          </p>

          {msg && <div className="bg-green-50 border border-green-200 text-green-700 rounded-lg px-4 py-3 text-sm mb-4">✓ {msg}</div>}
          {error && <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm mb-4">{error}</div>}

          <div className="bg-white border border-gray-200 rounded-lg p-4 mb-5 flex items-end gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Year</label>
              <input type="number" value={genYear} onChange={e => setGenYear(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-28" />
            </div>
            <button onClick={handleGenerate} disabled={generating}
              className="bg-indigo-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
              {generating ? 'Generating…' : '⚙ Generate Now (test)'}
            </button>
            <p className="text-xs text-gray-400">Dev/testing convenience — bypasses the automatic 7-day trigger.</p>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
            {loading ? (
              <div className="p-8 flex justify-center">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
              </div>
            ) : summaries.length === 0 ? (
              <div className="p-8 text-center text-gray-400 text-sm">No annual summaries generated yet.</div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-400 uppercase border-b border-gray-100">
                    <th className="py-2 px-4">Year</th>
                    <th className="py-2 px-4">Status</th>
                    <th className="py-2 px-4">Generated At</th>
                    <th className="py-2 px-4">Totals</th>
                    <th className="py-2 px-4">Download</th>
                  </tr>
                </thead>
                <tbody>
                  {summaries.map(s => (
                    <tr key={s.id} className="border-b border-gray-50">
                      <td className="py-2 px-4 font-semibold text-gray-800">{s.year}</td>
                      <td className="py-2 px-4">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_CLASSES[s.status]}`}>{STATUS_LABELS[s.status]}</span>
                      </td>
                      <td className="py-2 px-4 text-gray-500">{s.generated_at ? new Date(s.generated_at).toLocaleString('en-KE') : '—'}</td>
                      <td className="py-2 px-4 text-gray-500">
                        {s.summary_totals
                          ? `${s.summary_totals.total_delegates} delegates · KES ${Number(s.summary_totals.total_income).toLocaleString('en-KE')} income`
                          : '—'}
                      </td>
                      <td className="py-2 px-4">
                        {s.status === 'generated' ? (
                          <div className="flex gap-3">
                            <button onClick={() => handleDownload(s.year, 'xlsx')} className="text-blue-600 hover:underline text-xs">Excel</button>
                            <button onClick={() => handleDownload(s.year, 'pdf')} className="text-blue-600 hover:underline text-xs">PDF</button>
                          </div>
                        ) : s.status === 'failed' ? (
                          <span className="text-xs text-red-500" title={s.error_message}>Failed — hover for details</span>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </main>
      </div>
    </InactivityGuard>
  );
}
