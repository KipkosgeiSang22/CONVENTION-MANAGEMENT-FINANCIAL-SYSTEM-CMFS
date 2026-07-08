/**
 * FILE: cmfs/cmfs_frontend/pages/auth/setup.js
 *
 * Flow (mirrors reset-password.js's corrected step order):
 *   Step 1 'password' — choose a password → POST /api/auth/setup/totp-init/ { token }
 *                        (unauthenticated — identified by the one-time setup_token,
 *                        since a brand-new user has no JWT yet) to get a QR code
 *   Step 2 'totp'      — scan QR, enter code → POST /api/auth/setup/ { token, password, totp_code }
 *                        finalizes the account and returns the REAL recovery codes
 *   Step 3 'recovery'  — show the recovery codes just returned, require acknowledgment
 *   Step 4 'done'      — redirect to login
 */

import { useState } from 'react';
import { useRouter } from 'next/router';
import { api } from '../../lib/api';

export default function AccountSetupPage() {
  const router = useRouter();
  const { token } = router.query;

  const [step, setStep] = useState('password');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [qrDataUri, setQrDataUri] = useState('');
  const [totpUri, setTotpUri] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState([]);
  const [recoveryAcknowledged, setRecoveryAcknowledged] = useState(false);
  const [totpCode, setTotpCode] = useState('');

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // ── Step 1: choose password, initiate TOTP ─────────────────────────────────
  async function handlePasswordNext(e) {
    e.preventDefault();
    setError('');
    if (password !== confirm) { setError('Passwords do not match.'); return; }
    if (!token) { setError('Missing setup token. Please use the link from your invitation.'); return; }
    setLoading(true);
    try {
      const res = await api.post('/api/auth/setup/totp-init/', { token });
      if (!res.ok) throw new Error(res.data?.error || 'Setup failed.');
      setQrDataUri(res.data.qr_data_uri);
      setTotpUri(res.data.totp_uri);
      setStep('totp');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Step 2: verify TOTP + finalize account ──────────────────────────────────
  async function handleSetupComplete(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.post('/api/auth/setup/', { token, password, totp_code: totpCode });
      if (!res.ok) throw new Error(res.data?.error || 'Setup failed.');
      setRecoveryCodes(res.data.recovery_codes || []);
      setStep('recovery');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Recovery codes download helper ─────────────────────────────────────────
  function downloadRecoveryCodes() {
    const text = [
      'KSCF Convention System — Recovery Codes',
      'Store these in a safe place. Each code can only be used ONCE.',
      '',
      ...recoveryCodes,
      '',
      `Generated: ${new Date().toISOString()}`,
    ].join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'kscf-recovery-codes.txt';
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="bg-white shadow rounded-lg p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">Set Up Your Account</h1>

        {step === 'password' && (
          <>
            <p className="text-gray-500 mb-6">Choose a password for your account.</p>
            <form onSubmit={handlePasswordNext} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input type="password" required autoComplete="new-password" value={password} onChange={e => setPassword(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
                <p className="text-xs text-gray-400 mt-1">Min 8 chars, include a number and a symbol.</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Confirm Password</label>
                <input type="password" required autoComplete="new-password" value={confirm} onChange={e => setConfirm(e.target.value)}
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
              Can't scan? Enter this key manually: <code>{totpUri}</code>
            </p>
            <form onSubmit={handleSetupComplete} className="space-y-4">
              <input type="text" inputMode="numeric" pattern="[0-9]{6}" maxLength={6}
                placeholder="000000" required value={totpCode} onChange={e => setTotpCode(e.target.value.replace(/\D/g, ''))}
                className="w-full border border-gray-300 rounded px-3 py-2 text-center text-xl tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-500" />
              {error && <p className="text-red-600 text-sm">{error}</p>}
              <button type="submit" disabled={loading}
                className="w-full bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50">
                {loading ? 'Verifying…' : 'Complete Setup'}
              </button>
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
            <button type="button" onClick={downloadRecoveryCodes}
              className="w-full border border-blue-600 text-blue-600 py-2 rounded font-medium hover:bg-blue-50 mb-4">
              ↓ Download Recovery Codes
            </button>
            <label className="flex items-start gap-3 text-sm text-gray-700 mb-4 cursor-pointer">
              <input type="checkbox" className="mt-0.5 accent-blue-600"
                checked={recoveryAcknowledged} onChange={e => setRecoveryAcknowledged(e.target.checked)} />
              <span>I have saved my recovery codes in a safe place.</span>
            </label>
            <button type="button" onClick={() => setStep('done')} disabled={!recoveryAcknowledged}
              className="w-full bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-40">
              Finish →
            </button>
          </>
        )}

        {step === 'done' && (
          <div className="text-center">
            <div className="text-green-500 text-5xl mb-4">✓</div>
            <h2 className="text-xl font-bold text-gray-800 mb-2">Account ready!</h2>
            <p className="text-gray-500 mb-6">Your account has been set up successfully.</p>
            <a href="/auth/login" className="bg-blue-600 text-white px-6 py-2 rounded font-medium hover:bg-blue-700">
              Sign In
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
