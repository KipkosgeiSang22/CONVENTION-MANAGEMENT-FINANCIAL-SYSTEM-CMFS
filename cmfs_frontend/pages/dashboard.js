import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { getUser, logout, refreshToken } from '../lib/auth';
import InactivityGuard from '../components/InactivityGuard';

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState(null);

  useEffect(() => {
    const u = getUser();
    if (!u) {
      // Try to refresh first
      refreshToken().then(ok => {
        if (!ok) router.replace('/auth/login');
      });
      return;
    }
    setUser(u);
  }, []);

  async function handleLogout() {
    await logout();
    router.replace('/auth/login');
  }

  if (!user) return (
    <div className="min-h-screen flex items-center justify-center text-gray-400">Loading…</div>
  );

  return (
    <InactivityGuard>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow px-6 py-4 flex justify-between items-center">
          <h1 className="text-xl font-bold text-gray-800">KSCF Convention System</h1>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm font-medium text-gray-700">{user.full_name}</p>
              <p className="text-xs text-gray-400">{user.role.replace('_', ' ')}</p>
              {user.last_login_at && (
                <p className="text-xs text-gray-400">
                  Last login: {new Date(user.last_login_at).toLocaleString('en-KE')}
                  {user.last_login_ip ? ` from ${user.last_login_ip}` : ''}
                </p>
              )}
            </div>
            <button onClick={handleLogout}
              className="text-sm text-red-600 hover:underline">
              Log Out
            </button>
          </div>
        </header>
        <main className="p-6">
          <p className="text-gray-500">Dashboard — Phase 3 will build this out.</p>
        </main>
      </div>
    </InactivityGuard>
  );
}