import { useState } from 'react';
import { useRouter } from 'next/router';
import { login, verifyTotp, useRecoveryCode } from '../../lib/auth';

export default function LoginPage() {
  const router = useRouter();

  // Steps: 'credentials' | 'totp' | 'recovery'
  const [step, setStep] = useState('credentials');
  const [partialToken, setPartialToken] = useState('');

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [recoveryCode, setRecoveryCode] = useState('');

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleCredentials(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const result = await login(email, password);
      if (result.requiresTotp) {
        setPartialToken(result.partialToken);
        setStep('totp');
      } else {
        router.replace('/dashboard');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleTotp(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await verifyTotp(partialToken, totpCode);
      router.replace('/dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRecovery(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await useRecoveryCode(partialToken, recoveryCode);
      router.replace('/dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white shadow rounded-lg p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">KSCF Convention System</h1>

        {step === 'credentials' && (
          <>
            <p className="text-gray-500 mb-6">Sign in to your account</p>
            <form onSubmit={handleCredentials} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email" required autoFocus
                  value={email} onChange={e => setEmail(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input
                  type="password" required
                  value={password} onChange={e => setPassword(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              {error && <p className="text-red-600 text-sm">{error}</p>}
              <button
                type="submit" disabled={loading}
                className="w-full bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Signing in…' : 'Sign In'}
              </button>
              <p className="text-center text-sm">
                <a href="/auth/forgot-password" className="text-blue-600 hover:underline">Forgot password?</a>
              </p>
            </form>
          </>
        )}

        {step === 'totp' && (
          <>
            <p className="text-gray-500 mb-6">Enter the 6-digit code from your authenticator app.</p>
            <form onSubmit={handleTotp} className="space-y-4">
              <input
                type="text" inputMode="numeric" pattern="[0-9]{6}" maxLength={6}
                autoFocus required placeholder="000000"
                value={totpCode} onChange={e => setTotpCode(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2 text-center text-xl tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {error && <p className="text-red-600 text-sm">{error}</p>}
              <button type="submit" disabled={loading}
                className="w-full bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50">
                {loading ? 'Verifying…' : 'Verify'}
              </button>
              <p className="text-center text-sm">
                <button type="button" onClick={() => { setStep('recovery'); setError(''); }}
                  className="text-blue-600 hover:underline">
                  Use a recovery code instead
                </button>
              </p>
            </form>
          </>
        )}

        {step === 'recovery' && (
          <>
            <p className="text-gray-500 mb-6">Enter one of your 8 recovery codes.</p>
            <form onSubmit={handleRecovery} className="space-y-4">
              <input
                type="text" autoFocus required placeholder="XXXXXXXXXX"
                value={recoveryCode} onChange={e => setRecoveryCode(e.target.value.toUpperCase())}
                className="w-full border border-gray-300 rounded px-3 py-2 font-mono text-center tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {error && <p className="text-red-600 text-sm">{error}</p>}
              <button type="submit" disabled={loading}
                className="w-full bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50">
                {loading ? 'Verifying…' : 'Use Recovery Code'}
              </button>
              <p className="text-center text-sm">
                <button type="button" onClick={() => { setStep('totp'); setError(''); }}
                  className="text-blue-600 hover:underline">
                  ← Back to TOTP
                </button>
              </p>
            </form>
          </>
        )}
      </div>
    </div>
  );
}