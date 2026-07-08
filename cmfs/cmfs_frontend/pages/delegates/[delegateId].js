/**
 * FILE: cmfs/cmfs_frontend/pages/delegates/[delegateId].js
 * ACTION: CREATE (Phase 6)
 *
 * Public — no login required. `delegateId` is the human-readable code
 * (e.g. KER-STU-2026-0042), reached via the confirmation email link.
 * QR code display arrives in Phase 7 (qr_code_path exists on the model
 * but isn't rendered here yet).
 */

import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { getDelegate, CATEGORY_LABELS, PAYMENT_STATUS_STYLES, fmtKES } from '../../lib/delegates';

export default function DelegateStatusPage() {
  const router = useRouter();
  const { delegateId } = router.query;

  const [delegate, setDelegate] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!delegateId) return;
    (async () => {
      const res = await getDelegate(delegateId);
      if (res.ok) setDelegate(res.data.delegate);
      else setError(res.data?.error || 'Delegate not found.');
      setLoading(false);
    })();
  }, [delegateId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error || !delegate) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 text-center px-4">
        <div className="text-5xl mb-3">🔍</div>
        <p className="text-gray-600">{error || 'Delegate not found.'}</p>
      </div>
    );
  }

  const badge = PAYMENT_STATUS_STYLES[delegate.payment_status] || PAYMENT_STATUS_STYLES.PENDING;

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-md mx-auto bg-white border border-gray-200 rounded-lg p-6">
        <div className="text-center mb-6">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Delegate ID</p>
          <p className="text-2xl font-mono font-bold text-gray-900">{delegate.delegate_id}</p>
        </div>

        <div className="space-y-3 text-sm">
          <Row label="Name" value={delegate.full_name} />
          <Row label="Category" value={CATEGORY_LABELS[delegate.category] || delegate.category} />
          <Row label="County" value={delegate.county_name} />
          <Row label="Email" value={delegate.email} />
          <Row label="Registered" value={new Date(delegate.registration_date).toLocaleDateString()} />
        </div>

        <div className="mt-5 pt-5 border-t border-gray-100 space-y-3 text-sm">
          <Row label="Fee" value={fmtKES(delegate.fee_amount)} />
          <Row label="Paid" value={fmtKES(delegate.total_paid)} />
          <Row label="Balance" value={fmtKES(delegate.balance_owed)} />
          <div className="flex items-center justify-between">
            <span className="text-gray-500">Status</span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${badge.bg} ${badge.text}`}>
              {badge.label}
            </span>
          </div>
        </div>

        {delegate.balance_owed > 0 && (
          <p className="mt-5 text-xs text-gray-400 text-center">
            To pay the remaining balance, see your County Budget Creator at the convention venue.
          </p>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-900 font-medium">{value}</span>
    </div>
  );
}