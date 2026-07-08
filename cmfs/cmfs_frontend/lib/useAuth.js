/**
 * Shared hook: restores auth state on page load/refresh.
 * Returns { user, loading } — redirects to /auth/login if not authenticated.
 */
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { getUser, refreshToken } from './auth';
import { api } from './api';

export default function useAuth() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function init() {
      // Already in memory (same-session navigation)
      const u = getUser();
      if (u) { setUser(u); setLoading(false); return; }

      // Try refresh cookie
      const ok = await refreshToken();
      if (!ok) { router.replace('/auth/login'); return; }

      // Refresh worked — fetch profile
      try {
        const res = await api.get('/api/auth/me/');
        if (res.ok && res.data?.user) {
          setUser(res.data.user);
        } else {
          router.replace('/auth/login');
        }
      } catch {
        router.replace('/auth/login');
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  return { user, loading };
}