/**
 * FILE: cmfs/cmfs_frontend/components/gate/ScanResultModal.js
 * ACTION: CREATE (Phase 8)
 *
 * Renders whichever of the 5 scan-result states applies:
 *   complete           — payment complete, offer "Mark as Attended"
 *   incomplete         — balance owed, offer cash-at-gate (online only) or deny
 *   already            — already checked in (shows first check-in time + officer)
 *   not_found_online   — QR didn't match anything in the cached list, and we can verify online
 *   not_found_offline  — same, but we're offline so it might just be stale local data
 */
import { useState } from 'react';

export default function ScanResultModal({
  result, online, onClose, onMarkAttended, onOpenCashPayment, marking,
}) {
  if (!result) return null;
  const { type, delegate } = result;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 text-center">

        {type === 'complete' && (
          <>
            <p className="text-4xl mb-2">✅</p>
            <h3 className="text-lg font-bold text-green-700 mb-1">PAYMENT COMPLETE</h3>
            <p className="text-sm text-gray-600 mb-1">{delegate.full_name}</p>
            <p className="text-xs text-gray-400 mb-5">{delegate.delegate_id} · {delegate.category}</p>
            <button
              onClick={() => onMarkAttended(delegate)}
              disabled={marking}
              className="w-full bg-green-600 text-white rounded-lg py-3 text-sm font-semibold hover:bg-green-700 disabled:opacity-50 mb-3"
            >
              {marking ? 'Marking…' : 'Mark as Attended'}
            </button>
          </>
        )}

        {type === 'incomplete' && (
          <>
            <p className="text-4xl mb-2">⚠️</p>
            <h3 className="text-lg font-bold text-amber-600 mb-1">INCOMPLETE PAYMENT</h3>
            <p className="text-sm text-gray-600 mb-1">{delegate.full_name}</p>
            <p className="text-xs text-gray-400 mb-3">{delegate.delegate_id} · {delegate.category}</p>
            <p className="text-sm text-gray-700 mb-5">
              Balance owed: <strong>KES {Number(delegate.balance_owed).toLocaleString()}</strong>
            </p>
            {online ? (
              <button
                onClick={() => onOpenCashPayment(delegate)}
                className="w-full bg-blue-600 text-white rounded-lg py-3 text-sm font-semibold hover:bg-blue-700 mb-3"
              >
                Collect Cash Payment
              </button>
            ) : (
              <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg py-2 px-3 mb-3">
                Cash payments require an internet connection.
              </p>
            )}
            <button
              onClick={onClose}
              className="w-full border border-gray-300 text-gray-700 rounded-lg py-2.5 text-sm font-medium hover:bg-gray-50"
            >
              Deny Entry
            </button>
          </>
        )}

        {type === 'already' && (
          <>
            <p className="text-4xl mb-2">🔁</p>
            <h3 className="text-lg font-bold text-gray-800 mb-1">ALREADY CHECKED IN</h3>
            <p className="text-sm text-gray-600 mb-1">{delegate.full_name}</p>
            <p className="text-xs text-gray-400 mb-4">{delegate.delegate_id}</p>
            <p className="text-sm text-gray-500">
              Checked in {delegate.checked_in_at ? new Date(delegate.checked_in_at).toLocaleString('en-KE') : ''}
              {delegate.checked_in_by_name ? ` by ${delegate.checked_in_by_name}` : ''}
            </p>
          </>
        )}

        {type === 'not_found_online' && (
          <>
            <p className="text-4xl mb-2">❌</p>
            <h3 className="text-lg font-bold text-red-600 mb-2">DELEGATE NOT FOUND</h3>
            <p className="text-sm text-gray-500">Ask for Delegate ID or registration email.</p>
          </>
        )}

        {type === 'not_found_offline' && (
          <>
            <p className="text-4xl mb-2">❌</p>
            <h3 className="text-lg font-bold text-red-600 mb-2">DELEGATE NOT FOUND</h3>
            <p className="text-sm text-gray-500 mb-2">
              You're offline, so this could just mean they registered after your last sync.
            </p>
            <p className="text-sm text-gray-500">Ask for Delegate ID or registration email, or reconnect and try again.</p>
          </>
        )}

        <button onClick={onClose} className="mt-5 text-xs text-gray-400 hover:underline">
          Close
        </button>
      </div>
    </div>
  );
}
