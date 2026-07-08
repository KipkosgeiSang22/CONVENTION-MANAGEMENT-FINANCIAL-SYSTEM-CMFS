/**
 * FILE: cmfs/cmfs_frontend/pages/register/status/[id].js
 * ACTION: CREATE (Phase 6)
 *
 * Public "Awaiting payment" holding page. `id` is the internal Delegate
 * pk returned by POST /api/delegates/register/ (registration_id) —
 * NOT the human Delegate ID, which doesn't exist until payment confirms.
 * Polls every 4s until the payment resolves one way or another.
 */

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { getRegistrationStatus, fmtKES } from '../../../lib/delegates';
import { initiateMpesa } from '../../../lib/payments';

const POLL_MS = 4000;

export default function RegistrationStatusPage() {
  const router = useRouter();
  const { id, amount } = router.query;

  const [status, setStatus] = useState(null); // { registration_status, delegate_id, payment_status }
  const [error, setError] = useState('');
  const [retrying, setRetrying] = useState(false);
  const [retryMessage, setRetryMessage] = useState('');
  const timerRef = useRef(null);

  useEffect(() => {
    if (!id) return;
    poll();
    return () => clearTimeout(timerRef.current);
  }, [id]);

  async function poll() {
    const res = await getRegistrationStatus(id);
    if (!res.ok) {
      setError('Could not check registration status.');
      return;
    }
    setStatus(res.data);

    const settled = res.data.registration_status !== 'pending' ||
      ['failed', 'timeout'].includes(res.data.payment_status);

    if (!settled) {
      timerRef.current = setTimeout(poll, POLL_MS);
    }
  }

  async function handleRetry() {
    setRetrying(true);
    setRetryMessage('');
    const res = await initiateMpesa(Number(id), amount);
    setRetrying(false);
    if (res.ok) {
      setRetryMessage('A new M-Pesa prompt has been sent — check the parent/guardian phone.');
      poll();
    } else {
      setRetryMessage(res.data?.error?.error || res.data?.error || 'Could not resend the payment prompt.');
    }
  }

  if (error) {
    return <Centered><p className="text-red-600">{error}</p></Centered>;
  }

  if (!status) {
    return <Centered><Spinner label="Loading…" /></Centered>;
  }

  // Confirmed
  if (status.registration_status !== 'pending' && status.delegate_id) {
    return (
      <Centered>
        <div className="text-5xl mb-3">✅</div>
        <h1 className="text-xl font-bold text-gray-900 mb-1">Registration Confirmed!</h1>
        <p className="text-gray-500 mb-4">Delegate ID: <span className="font-mono font-semibold">{status.delegate_id}</span></p>
        <p className="text-sm text-gray-500 mb-6">A confirmation email with your QR code is on its way.</p>
        <Link href={`/delegates/${status.delegate_id}`} className="text-blue-600 text-sm font-medium hover:underline">
          View delegate status →
        </Link>
      </Centered>
    );
  }

  // Failed or timed out — offer retry
  if (['failed', 'timeout'].includes(status.payment_status)) {
    return (
      <Centered>
        <div className="text-5xl mb-3">⚠️</div>
        <h1 className="text-xl font-bold text-gray-900 mb-1">Payment Not Completed</h1>
        <p className="text-gray-500 mb-4 text-sm">
          {status.payment_status === 'timeout'
            ? 'The M-Pesa prompt timed out before it was completed.'
            : 'The M-Pesa payment failed or was cancelled.'}
        </p>
        {retryMessage && <p className="text-sm text-blue-600 mb-3">{retryMessage}</p>}
        <button onClick={handleRetry} disabled={retrying}
          className="bg-blue-600 text-white rounded-lg px-5 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
          {retrying ? 'Sending…' : `Resend Payment Prompt (${fmtKES(amount)})`}
        </button>
      </Centered>
    );
  }

  // Still pending
  return (
    <Centered>
      <Spinner label="Waiting for M-Pesa confirmation…" />
      <p className="text-sm text-gray-500 mt-3 max-w-xs">
        Check the parent/guardian's phone for the M-Pesa PIN prompt and enter their PIN to complete payment
        {amount ? ` of ${fmtKES(amount)}` : ''}.
      </p>
    </Centered>
  );
}

function Centered({ children }) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center text-center px-4">
      {children}
    </div>
  );
}

function Spinner({ label }) {
  return (
    <div className="flex flex-col items-center">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mb-3" />
      <p className="text-gray-600 text-sm">{label}</p>
    </div>
  );
}