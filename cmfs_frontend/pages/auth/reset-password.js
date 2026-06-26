import { useState } from 'react';
import { useRouter } from 'next/router';
import { api } from '../../lib/api';

export default function ResetPasswordPage() {
  const router = useRouter();
  const { token } = router.query;

  const [step, setStep] = useState('password'); // 'password' | 'totp'
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (password !== confirm) { setError('Passwords do not match.'); return; }
    setLoading(true);
    try {
      const res = await api.post('/api/auth/password-reset/confirm/', {
        token, password, totp_code: totpCode
      });
      if (!res.ok) throw new Error(res.data?.error || 'Reset failed');
      setDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (done) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white shadow rounded-lg p-8 w-full max-w-md text-center">
        <div className="text-green-500 text-5xl mb-4">✓</div>
        <h2 className="text-xl font-bold text-gray-800 mb-2">Password reset!</h2>
        <p className="text-gray-500 mb-6">Your password has been updated. All previous sessions have been ended.</p>
        <a href="/auth/login" className="bg-blue-600 text-white px-6 py-2 rounded font-medium hover:bg-blue-700">Sign In</a>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white shadow rounded-lg p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">Reset Password</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
            <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Confirm New Password</label>
            <input type="password" required value={confirm} onChange={e => setConfirm(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">TOTP Code (if you have it)</label>
            <input type="text" inputMode="numeric" maxLength={6} placeholder="000000"
              value={totpCode} onChange={e => setTotpCode(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 text-center tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-500" />
            <p className="text-xs text-gray-400 mt-1">Leave blank if TOTP was already reset by admin.</p>
          </div>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <button type="submit" disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50">
            {loading ? 'Resetting…' : 'Reset Password'}
          </button>
        </form>
      </div>
    </div>
  );
}