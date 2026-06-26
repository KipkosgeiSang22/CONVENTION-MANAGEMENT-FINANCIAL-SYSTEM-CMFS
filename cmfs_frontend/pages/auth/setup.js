import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { api } from '../../lib/api';

const STEPS = ['password', 'totp', 'recovery'];

export default function AccountSetupPage() {
  const router = useRouter();
  const { token } = router.query;

  const [step, setStep] = useState('password');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [qrDataUri, setQrDataUri] = useState('');
  const [totpUri, setTotpUri] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState([]);
  const [totpCode, setTotpCode] = useState('');
  const [recoveryConfirmed, setRecoveryConfirmed] = useState(false);

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  async function handlePasswordNext(e) {
    e.preventDefault();
    setError('');
    if (password !== confirm) { setError('Passwords do not match.'); return; }
    setLoading(true);
    try {
      // Initiate TOTP setup to get QR
      const res = await api.post('/api/auth/totp/setup/', {});
      if (!res.ok) throw new Error(res.data?.error || 'Setup failed');
      setQrDataUri(res.data.qr_data_uri);
      setTotpUri(res.data.totp_uri);
      setRecoveryCodes(res.data.recovery_codes);
      setStep('totp');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSetupComplete(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.post('/api/auth/setup/', { token, password, totp_code: totpCode });
      if (!res.ok) throw new Error(res.data?.error || 'Setup failed');
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
        <h2 className="text-xl font-bold text-gray-800 mb-2">Account ready!</h2>
        <p className="text-gray-500 mb-6">Your account has been set up successfully.</p>
        <a href="/auth/login" className="bg-blue-600 text-white px-6 py-2 rounded font-medium hover:bg-blue-700">
          Sign In
        </a>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white shadow rounded-lg p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">Set Up Your Account</h1>

        {step === 'password' && (
          <>
            <p className="text-gray-500 mb-6">Choose a password for your account.</p>
            <form onSubmit={handlePasswordNext} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
                <p className="text-xs text-gray-400 mt-1">Min 8 chars, include a number and a symbol.</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Confirm Password</label>
                <input type="password" required value={confirm} onChange={e => setConfirm(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              {error && <p className="text-red-600 text-sm">{error}</p>}
              <button type="submit" disabled={loading}
                className="w-full bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50">
                {loading ? 'Loading…' : 'Next →'}
              </button>
            </form>
          </>
        )}

        {step === 'totp' && (
          <>
            <p className="text-gray-500 mb-4">Scan this QR code with <strong>Google Authenticator</strong>, then enter the 6-digit code to confirm.</p>
            {qrDataUri && <img src={qrDataUri} alt="TOTP QR Code" className="mx-auto mb-4 w-48 h-48" />}
            <p className="text-xs text-gray-400 mb-4 text-center break-all">
              Or enter manually: <code>{totpUri}</code>
            </p>
            <button type="button" onClick={() => setStep('recovery')}
              className="w-full bg-gray-100 text-gray-700 py-2 rounded font-medium hover:bg-gray-200 mb-4">
              View Recovery Codes First
            </button>
            <form onSubmit={handleSetupComplete} className="space-y-4">
              <input type="text" inputMode="numeric" pattern="[0-9]{6}" maxLength={6}
                placeholder="000000" required value={totpCode} onChange={e => setTotpCode(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2 text-center text-xl tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-500" />
              {error && <p className="text-red-600 text-sm">{error}</p>}
              <button type="submit" disabled={loading || !recoveryConfirmed}
                className="w-full bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50">
                {loading ? 'Saving…' : 'Complete Setup'}
              </button>
              {!recoveryConfirmed && (
                <p className="text-xs text-amber-600 text-center">You must view and save your recovery codes first.</p>
              )}
            </form>
          </>
        )}

        {step === 'recovery' && (
          <>
            <p className="text-amber-700 bg-amber-50 border border-amber-200 rounded p-3 text-sm mb-4">
              ⚠️ Save these codes now. They will <strong>never be shown again</strong>. Each code can only be used once.
            </p>
            <div className="bg-gray-50 rounded p-4 mb-4 grid grid-cols-2 gap-2">
              {recoveryCodes.map((code, i) => (
                <code key={i} className="font-mono text-sm bg-white border rounded px-2 py-1 text-center">{code}</code>
              ))}
            </div>
            <button type="button" onClick={() => { setRecoveryConfirmed(true); setStep('totp'); }}
              className="w-full bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700">
              I have saved my recovery codes →
            </button>
          </>
        )}
      </div>
    </div>
  );
}