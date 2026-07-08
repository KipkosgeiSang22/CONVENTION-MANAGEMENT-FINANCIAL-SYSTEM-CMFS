/**
 * FILE: cmfs/cmfs_frontend/pages/auth/reset-password.js
 * ACTION: REPLACE (Phase 2 completion)
 *
 * Flow:
 *   Step 1 'password'  — enter + confirm new password → POST /api/auth/password-reset/confirm/
 *   Step 2 'totp_setup' — backend cleared TOTP; fetch new QR via /api/auth/totp/setup/
 *                          (using a short-lived post-reset access token returned by the confirm endpoint)
 *   Step 3 'qr'         — show QR code + TOTP URI to scan in Google Authenticator
 *   Step 4 'verify_totp'— enter first 6-digit code to confirm setup → POST /api/auth/totp/confirm/
 *   Step 5 'recovery'   — show the 8 recovery codes returned by the confirm call (download link), user must acknowledge
 *   Step 6 'done'       — redirect prompt
 */

import { useState } from 'react';
import { useRouter } from 'next/router';
import { api } from '../../lib/api';

export default function ResetPasswordPage() {
  const router = useRouter();
  const { token } = router.query;

  const [step, setStep] = useState('password'); // see flow above
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Post-reset ephemeral access token (used only for TOTP setup calls)
  const [resetAccessToken, setResetAccessToken] = useState('');

  // TOTP setup state
  const [qrDataUri, setQrDataUri] = useState('');
  const [totpUri, setTotpUri] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState([]);
  const [recoveryAcknowledged, setRecoveryAcknowledged] = useState(false);
  const [totpCode, setTotpCode] = useState('');

  // ── Step 1: Password reset ──────────────────────────────────────────────────
  async function handlePasswordSubmit(e) {
    e.preventDefault();
    setError('');
    if (password !== confirm) { setError('Passwords do not match.'); return; }
    if (!token) { setError('Missing reset token. Please use the link from your email.'); return; }
    setLoading(true);
    try {
      const res = await api.post('/api/auth/password-reset/confirm/', { token, password });
      if (!res.ok) throw new Error(res.data?.error || 'Reset failed.');
      // Backend returns { message, totp_reset: true, setup_access_token }
      // The setup_access_token is a short-lived access token allowing /totp/setup/ call
      setResetAccessToken(res.data?.setup_access_token || '');
      setStep('totp_setup');
      await initiateTOTPSetup(res.data?.setup_access_token || '');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Step 2: Initiate TOTP re-setup ─────────────────────────────────────────
  async function initiateTOTPSetup(accessToken) {
    setLoading(true);
    setError('');
    try {
      const res = await api.post('/api/auth/totp/setup/', {}, {
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      });
      if (!res.ok) throw new Error(res.data?.error || 'Failed to initiate TOTP setup.');
      setQrDataUri(res.data.qr_data_uri);
      setTotpUri(res.data.totp_uri);
      setStep('qr');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Step 5: Verify TOTP code to finalise setup ─────────────────────────────
  async function handleTOTPConfirm(e) {
    e.preventDefault();
    setError('');
    if (!totpCode || totpCode.length !== 6) {
      setError('Please enter the 6-digit code from your Authenticator app.');
      return;
    }
    setLoading(true);
    try {
      const res = await api.post('/api/auth/totp/confirm/', { code: totpCode }, {
        headers: resetAccessToken ? { Authorization: `Bearer ${resetAccessToken}` } : {},
      });
      if (!res.ok) throw new Error(res.data?.error || 'Invalid TOTP code. Try again.');
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

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="bg-white shadow rounded-lg p-8 w-full max-w-md">

        {/* ── Step: password ── */}
        {step === 'password' && (
          <>
            <h1 className="text-2xl font-bold text-gray-800 mb-1">Reset Password</h1>
            <p className="text-sm text-gray-500 mb-6">
              Enter your new password. Your Google Authenticator will need to be reconfigured afterwards.
            </p>
            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
                <input
                  type="password" required autoComplete="new-password"
                  value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="Min 8 chars, include number and symbol"
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Confirm New Password</label>
                <input
                  type="password" required autoComplete="new-password"
                  value={confirm} onChange={e => setConfirm(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              {error && <p className="text-red-600 text-sm">{error}</p>}
              <button
                type="submit" disabled={loading || !token}
                className="w-full bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Resetting…' : 'Set New Password'}
              </button>
            </form>
          </>
        )}

        {/* ── Step: totp_setup (loading) ── */}
        {step === 'totp_setup' && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto mb-4" />
            <p className="text-gray-600">Setting up your new Authenticator…</p>
            {error && <p className="text-red-600 text-sm mt-4">{error}</p>}
          </div>
        )}

        {/* ── Step: qr — Scan QR code ── */}
        {step === 'qr' && (
          <>
            <h2 className="text-xl font-bold text-gray-800 mb-1">Re-setup Google Authenticator</h2>
            <p className="text-sm text-gray-500 mb-4">
              Your Authenticator app was reset. Scan the QR code below to add the KSCF Convention System again.
            </p>

            {qrDataUri && (
              <div className="flex justify-center mb-4">
                <img src={qrDataUri} alt="TOTP QR Code" className="w-48 h-48 border border-gray-200 rounded" />
              </div>
            )}

            <p className="text-xs text-gray-400 mb-1 text-center">Can't scan? Enter this key manually:</p>
            <div className="bg-gray-50 border border-gray-200 rounded px-3 py-2 text-xs font-mono text-center text-gray-700 mb-6 break-all">
              {totpUri}
            </div>

            {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

            <button
              onClick={() => setStep('verify_totp')}
              className="w-full bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700"
            >
              I've Scanned the QR Code →
            </button>
          </>
        )}

        {/* ── Step: verify_totp — Enter first code to confirm ── */}
        {step === 'verify_totp' && (
          <>
            <h2 className="text-xl font-bold text-gray-800 mb-1">Verify Authenticator</h2>
            <p className="text-sm text-gray-500 mb-6">
              Enter the 6-digit code now showing in your Google Authenticator app to complete setup.
            </p>
            <form onSubmit={handleTOTPConfirm} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">6-Digit Code</label>
                <input
                  type="text" inputMode="numeric" pattern="\d{6}" maxLength={6}
                  placeholder="000000" required
                  value={totpCode} onChange={e => setTotpCode(e.target.value.replace(/\D/g, ''))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-center tracking-widest text-xl font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              {error && <p className="text-red-600 text-sm">{error}</p>}
              <button
                type="submit" disabled={loading}
                className="w-full bg-green-600 text-white py-2 rounded font-medium hover:bg-green-700 disabled:opacity-50"
              >
                {loading ? 'Verifying…' : 'Verify Code →'}
              </button>
            </form>
          </>
        )}

        {/* ── Step: recovery — Show the real recovery codes returned after verification ── */}
        {step === 'recovery' && (
          <>
            <h2 className="text-xl font-bold text-gray-800 mb-1">Save Your Recovery Codes</h2>
            <div className="bg-yellow-50 border border-yellow-300 rounded px-4 py-3 mb-4 text-sm text-yellow-800">
              ⚠️ These 8 codes are shown <strong>only once</strong>. Each is single-use.
              Save them somewhere safe — print them or store in a password manager.
            </div>

            <div className="grid grid-cols-2 gap-2 mb-4">
              {recoveryCodes.map((code, i) => (
                <div key={i} className="bg-gray-50 border border-gray-200 rounded px-3 py-2 text-sm font-mono text-center text-gray-800">
                  {code}
                </div>
              ))}
            </div>

            <button
              onClick={downloadRecoveryCodes}
              className="w-full border border-blue-600 text-blue-600 py-2 rounded font-medium hover:bg-blue-50 mb-4"
            >
              ↓ Download Recovery Codes
            </button>

            <label className="flex items-start gap-3 text-sm text-gray-700 mb-4 cursor-pointer">
              <input
                type="checkbox"
                className="mt-0.5 accent-blue-600"
                checked={recoveryAcknowledged}
                onChange={e => setRecoveryAcknowledged(e.target.checked)}
              />
              <span>I have saved my recovery codes in a safe place.</span>
            </label>

            <button
              onClick={() => setStep('done')}
              disabled={!recoveryAcknowledged}
              className="w-full bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-40"
            >
              Finish →
            </button>
          </>
        )}

        {/* ── Step: done ── */}
        {step === 'done' && (
          <div className="text-center">
            <div className="text-green-500 text-5xl mb-4">✓</div>
            <h2 className="text-xl font-bold text-gray-800 mb-2">All Set!</h2>
            <p className="text-gray-500 mb-2">Your password has been reset and Google Authenticator is configured.</p>
            <p className="text-gray-500 mb-6">All previous sessions have been ended for your security.</p>
            <a
              href="/auth/login"
              className="inline-block bg-blue-600 text-white px-6 py-2 rounded font-medium hover:bg-blue-700"
            >
              Sign In Now
            </a>
          </div>
        )}

      </div>
    </div>
  );
}
