import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { isLoggedIn } from '../lib/auth';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    if (isLoggedIn()) {
      router.replace('/dashboard');
    } else {
      router.replace('/auth/login');
    }
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <p className="text-gray-400 text-sm">Redirecting…</p>
    </div>
  );
}