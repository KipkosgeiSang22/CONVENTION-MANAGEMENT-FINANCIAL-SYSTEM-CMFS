import { useEffect, useState } from 'react';
import { checkHealth } from '../lib/api';

export default function Home() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    checkHealth()
      .then(({ ok, data }) => {
        if (ok) setHealth(data);
        else setError('Backend returned non-OK status');
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white shadow rounded-lg p-10 max-w-sm w-full text-center">
        <h1 className="text-2xl font-bold text-gray-800 mb-1">KSCF CMFS</h1>
        <p className="text-gray-500 text-sm mb-6">Convention Management &amp; Financial System</p>
        {loading && <p className="text-gray-400 text-sm">Checking backend…</p>}
        {error && <p className="text-red-600 text-sm font-medium">✗ {error}</p>}
        {health && <p className="text-green-600 text-sm font-medium">✓ Backend: {health.status} — DB: {health.db}</p>}
      </div>
    </main>
  );
}