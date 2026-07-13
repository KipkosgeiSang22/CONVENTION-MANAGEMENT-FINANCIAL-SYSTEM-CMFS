/**
 * FILE: cmfs/cmfs_frontend/components/DashboardWidgets.js
 * ACTION: CREATE (Phase 11)
 *
 * Renders whatever GET /api/dashboard/ returned, adapted to the caller's
 * role — see reports/dashboard_views.py for the exact payload shape per
 * role. No charting library: bars are just width-percentage divs, in
 * keeping with the rest of the app's minimal styling.
 */

import Link from 'next/link';

function kes(amount) {
  const n = Number(amount || 0);
  return `KES ${n.toLocaleString('en-KE', { maximumFractionDigits: 0 })}`;
}

function StatCard({ label, value, tone = 'default' }) {
  const toneClass = {
    default: 'text-gray-900',
    good: 'text-green-600',
    bad: 'text-red-600',
  }[tone];
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-xl font-bold ${toneClass}`}>{value}</p>
    </div>
  );
}

function IncomeVsBudgetChart({ bars }) {
  if (!bars || bars.length === 0) return null;
  const max = Math.max(1, ...bars.map(b => Math.max(b.budgeted, b.actual)));
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Income &amp; Expenditure vs Budget</h3>
      <div className="space-y-3">
        {bars.map((b, i) => (
          <div key={i}>
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>{b.label}</span>
              <span>{kes(b.actual)} / {kes(b.budgeted)} budgeted</span>
            </div>
            <div className="relative h-3 bg-gray-100 rounded-full overflow-hidden">
              <div className="absolute inset-y-0 left-0 bg-gray-300 rounded-full" style={{ width: `${(b.budgeted / max) * 100}%` }} />
              <div
                className={`absolute inset-y-0 left-0 rounded-full ${b.actual > b.budgeted ? 'bg-red-500' : 'bg-blue-600'}`}
                style={{ width: `${(b.actual / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function OutstandingItemsTable({ items }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 overflow-x-auto">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Outstanding Payments</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-400 uppercase border-b border-gray-100">
            <th className="py-1.5 pr-3">Delegate</th>
            <th className="py-1.5 pr-3">County</th>
            <th className="py-1.5 pr-3 text-right">Balance</th>
          </tr>
        </thead>
        <tbody>
          {items.slice(0, 10).map((row, i) => (
            <tr key={i} className="border-b border-gray-50">
              <td className="py-1.5 pr-3 text-gray-700">{row.delegate_name || row.name || '—'}</td>
              <td className="py-1.5 pr-3 text-gray-500">{row.county || '—'}</td>
              <td className="py-1.5 pr-3 text-right text-red-600 font-medium">{kes(row.balance_owed ?? row.balance)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {items.length > 10 && (
        <p className="text-xs text-gray-400 mt-2">+{items.length - 10} more — see Delegates for the full list.</p>
      )}
    </div>
  );
}

function BreakdownTable({ title, rows, nameKey, nameLabel }) {
  if (!rows || rows.length === 0) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 overflow-x-auto">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-400 uppercase border-b border-gray-100">
            <th className="py-1.5 pr-3">{nameLabel}</th>
            <th className="py-1.5 pr-3 text-right">Delegates</th>
            <th className="py-1.5 pr-3 text-right">Income</th>
            <th className="py-1.5 pr-3 text-right">Expenditure</th>
            <th className="py-1.5 pr-3 text-right">Net</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-gray-50">
              <td className="py-1.5 pr-3 text-gray-700">{row[nameKey]}</td>
              <td className="py-1.5 pr-3 text-right text-gray-600">{row.delegate_count}</td>
              <td className="py-1.5 pr-3 text-right text-gray-600">{kes(row.total_income)}</td>
              <td className="py-1.5 pr-3 text-right text-gray-600">{kes(row.total_expenditure)}</td>
              <td className={`py-1.5 pr-3 text-right font-medium ${row.net_balance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {kes(row.net_balance)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Super Admin: system-wide health counters + every convention. */
function SuperAdminDashboard({ data }) {
  const h = data.system_health;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Conventions" value={data.conventions.length} />
        <StatCard label="Failed Report Files" value={h.failed_report_files} tone={h.failed_report_files > 0 ? 'bad' : 'good'} />
        <StatCard label="Pending Report Files" value={h.pending_report_files} />
        <StatCard label="Audit Events (24h)" value={h.audit_log_events_last_24h} />
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-5 overflow-x-auto">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-700">All Conventions</h3>
          <Link href="/conventions" className="text-xs text-blue-600 hover:underline">View all →</Link>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-400 uppercase border-b border-gray-100">
              <th className="py-1.5 pr-3">Name</th>
              <th className="py-1.5 pr-3">Scope</th>
              <th className="py-1.5 pr-3">Status</th>
              <th className="py-1.5 pr-3 text-right">Units</th>
            </tr>
          </thead>
          <tbody>
            {data.conventions.slice(0, 8).map(c => (
              <tr key={c.id} className="border-b border-gray-50">
                <td className="py-1.5 pr-3 text-gray-700">
                  <Link href={`/conventions/${c.id}`} className="hover:text-blue-600 hover:underline">{c.name}</Link>
                </td>
                <td className="py-1.5 pr-3 text-gray-500 capitalize">{c.scope}</td>
                <td className="py-1.5 pr-3 text-gray-500 capitalize">{c.status.replace(/_/g, ' ')}</td>
                <td className="py-1.5 pr-3 text-right text-gray-500">{c.unit_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.recent_annual_summaries && data.recent_annual_summaries.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700">Annual Summaries</h3>
            <Link href="/annual-summary" className="text-xs text-blue-600 hover:underline">View all →</Link>
          </div>
          <div className="flex flex-wrap gap-2">
            {data.recent_annual_summaries.map(s => (
              <span key={s.year} className={`text-xs px-2.5 py-1 rounded-full ${
                s.status === 'generated' ? 'bg-green-50 text-green-700' :
                s.status === 'failed' ? 'bg-red-50 text-red-700' : 'bg-gray-100 text-gray-500'
              }`}>
                {s.year} — {s.status}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function DashboardWidgets({ data }) {
  if (!data) return null;

  if (data.role === 'super_admin') return <SuperAdminDashboard data={data} />;

  if (!data.has_live_convention) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-8 text-center text-gray-400">
        <p className="text-3xl mb-2">📭</p>
        <p className="text-sm">{data.message || 'No live convention right now.'}</p>
      </div>
    );
  }

  if (data.error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
        {data.error}
      </div>
    );
  }

  const totals = data.national_totals || data.regional_totals || (data.unit && {
    total_income: data.unit.total_income,
    total_expenditure: data.unit.total_expenditure,
    net_balance: data.unit.net_balance,
    delegate_count: data.unit.delegate_count,
    checked_in_count: data.unit.checked_in_count,
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-sm font-semibold text-gray-700">{data.convention_name}</h2>
        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded capitalize">
          {data.convention_status?.replace(/_/g, ' ')}
        </span>
      </div>

      {totals && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          <StatCard label="Delegates" value={totals.delegate_count} />
          <StatCard label="Checked In" value={totals.checked_in_count} />
          <StatCard label="Income" value={kes(totals.total_income)} />
          <StatCard label="Expenditure" value={kes(totals.total_expenditure)} />
          <StatCard label={totals.net_balance >= 0 ? 'Surplus' : 'Deficit'} value={kes(Math.abs(totals.net_balance))}
            tone={totals.net_balance >= 0 ? 'good' : 'bad'} />
        </div>
      )}

      {data.region_breakdown && (
        <BreakdownTable title="Region Breakdown" rows={data.region_breakdown} nameKey="region_name" nameLabel="Region" />
      )}
      {data.county_breakdown && (
        <BreakdownTable title="County Breakdown" rows={data.county_breakdown} nameKey="display_name" nameLabel="County" />
      )}

      <IncomeVsBudgetChart bars={data.income_vs_budget} />
      <OutstandingItemsTable items={data.outstanding_items} />
    </div>
  );
}
