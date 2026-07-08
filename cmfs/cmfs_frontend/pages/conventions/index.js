import { useState, useEffect } from 'react';
import Link from 'next/link';
import useAuth from '../../lib/useAuth';
import { listConventions, STATUS_LABELS, STATUS_COLORS } from '../../lib/conventions';

const FILTERS = ['all', 'draft', 'open', 'active', 'ended', 'financially_closed', 'archived'];

export default function ConventionsIndexPage() {
  const { user, loading: authLoading } = useAuth();
  const [conventions, setConventions] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => {
    if (!user) return;
    fetchConventions(statusFilter);
  }, [user, statusFilter]);

  async function fetchConventions(filter) {
    setLoading(true);
    setError('');
    try {
      const params = filter !== 'all' ? { status: filter } : {};
      const res = await listConventions(params);
      if (!res.ok) throw new Error(res.data?.error || 'Failed to load conventions.');
      setConventions(res.data.conventions || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (authLoading || !user) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/dashboard" className="text-gray-400 hover:text-gray-600 text-sm">← Dashboard</Link>
          <span className="text-gray-300">/</span>
          <h1 className="text-xl font-bold text-gray-900">Conventions</h1>
          <span className="text-sm text-gray-400">({total})</span>
        </div>
        {user.role === 'super_admin' && (
          <Link href="/conventions/new"
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition">
            + New Convention
          </Link>
        )}
      </div>

      {/* Filter tabs */}
      <div className="bg-white border-b border-gray-200 px-6">
        <div className="flex gap-0 overflow-x-auto">
          {FILTERS.map(f => (
            <button key={f} onClick={() => setStatusFilter(f)}
              className={`px-4 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition ${
                statusFilter === f
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}>
              {f === 'all' ? 'All' : STATUS_LABELS[f]}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-5xl mx-auto px-6 py-6">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-4 text-sm">{error}</div>
        )}

        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        ) : conventions.length === 0 ? (
          <div className="text-center py-20 text-gray-400">
            <div className="text-5xl mb-3">📋</div>
            <p className="font-medium text-gray-500">No conventions found</p>
            {user.role === 'super_admin' && (
              <p className="text-sm mt-2">
                <Link href="/conventions/new" className="text-blue-600 hover:underline">Create your first convention</Link>
              </p>
            )}
          </div>
        ) : (
          <div className="grid gap-3">
            {conventions.map(conv => (
              <Link key={conv.id} href={`/conventions/${conv.id}`}>
                <div className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md hover:border-blue-300 transition cursor-pointer">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <h3 className="text-base font-semibold text-gray-900">{conv.name}</h3>
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[conv.status]}`}>
                          {STATUS_LABELS[conv.status]}
                        </span>
                        <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 capitalize">
                          {conv.scope}
                        </span>
                        {conv.is_registration_open && (
                          <span className="text-xs text-green-600 font-medium">● Reg. Open</span>
                        )}
                      </div>
                      <p className="text-sm text-gray-500">
                        📅 {conv.start_date} → {conv.end_date} &nbsp;·&nbsp; {conv.unit_count} unit{conv.unit_count !== 1 ? 's' : ''}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-xs text-gray-400">Student fee</p>
                      <p className="text-sm font-semibold text-gray-800">KES {Number(conv.fee_student).toLocaleString()}</p>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}