/**
 * FILE: cmfs/cmfs_frontend/pages/dashboard.js
 * ACTION: REPLACE (Phase 4)
 * CHANGES:
 *  - Added Users nav card (visible to head roles)
 *  - Added scope context line under welcome (county / region / national)
 *  - Role label now includes scope label (e.g. "County Head — Nairobi County")
 *  - All Phase 2/3 logic unchanged.
 */

import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { getUser, logout, refreshToken } from '../lib/auth';
import { api } from '../lib/api';
import { getDashboard } from '../lib/dashboard';
import InactivityGuard from '../components/InactivityGuard';
import DashboardWidgets from '../components/DashboardWidgets';

const NAV_CARDS = [
  {
    title: 'Conventions',
    description: 'Create and manage conventions, track lifecycle status, generate reports.',
    href: '/conventions',
    icon: '📋',
    roles: ['super_admin', 'national_head', 'regional_head', 'county_head'],
  },
  {
    title: 'Users',
    description: 'Invite and manage users within your scope. View status and invalidate sessions.',
    href: '/users',
    icon: '👥',
    roles: ['super_admin', 'national_head', 'regional_head', 'county_head'],
  },
  {
    title: 'Budget',
    description: 'Enter income estimates and expense items; track live surplus/deficit.',
    href: '/budget',
    icon: '📊',
    roles: ['super_admin', 'national_head', 'regional_head', 'county_head', 'budget_creator', 'finance_viewer'],
  },
    {
    title: 'Delegates',
    description: 'Register delegates, track payment status, and record cash payments.',
    href: '/delegates',
    icon: '🧑‍🤝‍🧑',
    roles: ['super_admin', 'national_head', 'regional_head', 'county_head', 'budget_creator', 'finance_viewer'],
  },
  {
    title: 'Gate Check-In',
    description: 'Scan delegate QR codes, check in attendees, and collect balances at the gate.',
    href: '/gate',
    icon: '🚪',
    roles: ['super_admin', 'national_head', 'regional_head', 'county_head', 'gate_official'],
  },
  {
    title: 'Audit Log',
    description: 'Search and review every recorded system action, filterable by user, action, and date.',
    href: '/audit-logs',
    icon: '🛡️',
    roles: ['super_admin'],
  },
  {
    title: 'Annual Summary',
    description: 'Year-on-year totals across every convention, per-county surplus/deficit, and collection efficiency.',
    href: '/annual-summary',
    icon: '📅',
    roles: ['super_admin'],
  },
];

/** Build a scope context string from the user object. */
function getScopeLabel(user) {
  if (user.role === 'super_admin')    return 'All scopes';
  if (user.role === 'national_head')  return 'National';
  if (user.role === 'regional_head')  return user.region_name   ? `Region: ${user.region_name}`   : 'Regional';
  if (user.role === 'county_head')    return user.county_name   ? `County: ${user.county_name}`   : 'County';
  if (user.role === 'budget_creator') return user.county_name   ? `County: ${user.county_name}`   : 'County';
  if (user.role === 'finance_viewer') return user.county_name   ? `County: ${user.county_name}`   : 'County';
  if (user.role === 'gate_official')  return user.county_name   ? `County: ${user.county_name}`   : 'County';
  return '';
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser]   = useState(null);
  const [error, setError] = useState('');
  const [dashData, setDashData] = useState(null);
  const [dashLoading, setDashLoading] = useState(true);

  useEffect(() => {
    async function init() {
      const u = getUser();
      if (u) { setUser(u); return; }

      const ok = await refreshToken();
      if (!ok) { router.replace('/auth/login'); return; }

      try {
        const res = await api.get('/api/auth/me/');
        if (res.ok && res.data?.user) {
          setUser(res.data.user);
        } else {
          router.replace('/auth/login');
        }
      } catch {
        router.replace('/auth/login');
      }
    }

    const fallback = setTimeout(() => {
      if (!getUser()) {
        setError('Cannot reach backend. Check that the server is running.');
      }
    }, 5000);

    init().finally(() => clearTimeout(fallback));
  }, []);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    setDashLoading(true);
    getDashboard()
      .then(res => { if (!cancelled && res.ok) setDashData(res.data); })
      .finally(() => { if (!cancelled) setDashLoading(false); });
    return () => { cancelled = true; };
  }, [user]);

  async function handleLogout() {
    await logout();
    router.replace('/auth/login');
  }

  if (error) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="bg-white border border-red-200 rounded-lg p-8 max-w-sm w-full text-center shadow">
        <p className="text-red-600 font-medium mb-4">{error}</p>
        <button onClick={() => router.replace('/auth/login')} className="text-blue-600 text-sm hover:underline">
          Go to Login
        </button>
      </div>
    </div>
  );

  if (!user) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="flex flex-col items-center gap-3">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        <p className="text-gray-400 text-sm">Loading your dashboard…</p>
      </div>
    </div>
  );

  const visibleCards = NAV_CARDS.filter(c => c.roles.includes(user.role));
  const scopeLabel   = getScopeLabel(user);

  return (
    <InactivityGuard>
      <div className="min-h-screen bg-gray-50">

        {/* Top nav */}
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <span className="text-xl font-bold text-gray-900">KSCF CMFS</span>
            <span className="text-xs text-gray-400 hidden sm:block">Convention Management &amp; Financial System</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm font-medium text-gray-700">{user.full_name}</p>
              <p className="text-xs text-gray-400 capitalize">{user.role.replace(/_/g, ' ')}</p>
            </div>
            <button onClick={handleLogout} className="text-sm text-red-600 hover:underline">
              Log Out
            </button>
          </div>
        </header>

        <main className="max-w-5xl mx-auto px-6 py-8">

          {/* Welcome block */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900">
              Welcome back, {user.full_name.split(' ')[0]}
            </h2>
            <div className="flex flex-wrap items-center gap-3 mt-1">
              {scopeLabel && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-100">
                  {scopeLabel}
                </span>
              )}
              {user.last_login_at && (
                <p className="text-sm text-gray-400">
                  Last login: {new Date(user.last_login_at).toLocaleString('en-KE')}
                  {user.last_login_ip ? ` · ${user.last_login_ip}` : ''}
                </p>
              )}
            </div>
          </div>

          {/* Live dashboard data — role-adaptive, see DashboardWidgets */}
          <div className="mb-8">
            {dashLoading ? (
              <div className="bg-white border border-gray-200 rounded-lg p-8 flex justify-center">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
              </div>
            ) : (
              <DashboardWidgets data={dashData} />
            )}
          </div>

          {/* Nav cards */}
          {visibleCards.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {visibleCards.map(card => (
                <Link key={card.href} href={card.href}>
                  <div className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md hover:border-blue-300 transition cursor-pointer h-full">
                    <div className="text-3xl mb-3">{card.icon}</div>
                    <h3 className="text-base font-semibold text-gray-900 mb-1">{card.title}</h3>
                    <p className="text-sm text-gray-500">{card.description}</p>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-16 text-gray-400">
              <p className="text-4xl mb-3">🔒</p>
              <p>No modules available for your role yet.</p>
            </div>
          )}
        </main>
      </div>
    </InactivityGuard>
  );
}