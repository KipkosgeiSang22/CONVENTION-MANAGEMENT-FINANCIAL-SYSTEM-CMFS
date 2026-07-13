/**
 * FILE: cmfs/cmfs_frontend/components/gate/CashPaymentForm.js
 * ACTION: CREATE (Phase 8)
 *
 * Online-only. Rendered instead of the incomplete-payment result modal
 * once "Collect Cash Payment" is tapped. Submits straight to
 * POST /api/gate/checkin/cash-payment/, which records the payment and
 * checks the delegate in atomically server-side.
 */
import { useState } from 'react';

export default function CashPaymentForm({ delegate, onCancel, onSubmit, submitting }) {
  const [amount, setAmount] = useState(String(delegate.balance_owed));
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');

  function handleSubmit() {
    const value = parseFloat(amount);
    if (!value || value <= 0) { setError('Enter a valid amount greater than 0.'); return; }
    setError('');
    onSubmit(delegate, value, notes);
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-1">Collect Cash Payment</h3>
        <p className="text-sm text-gray-500 mb-4">{delegate.full_name} · {delegate.delegate_id}</p>

        <label className="block text-xs font-medium text-gray-500 mb-1">Amount (KES)</label>
        <input
          type="number"
          inputMode="decimal"
          min="0.01"
          step="0.01"
          value={amount}
          onChange={e => setAmount(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
          autoFocus
        />

        <label className="block text-xs font-medium text-gray-500 mb-1">Notes (optional)</label>
        <input
          type="text"
          value={notes}
          onChange={e => setNotes(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        {error && <p className="text-xs text-red-600 mb-3">{error}</p>}

        <div className="flex gap-3 mt-2">
          <button
            onClick={onCancel}
            disabled={submitting}
            className="flex-1 border border-gray-300 text-gray-700 rounded-lg py-2.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1 bg-blue-600 text-white rounded-lg py-2.5 text-sm font-semibold hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? 'Recording…' : 'Record Payment & Check In'}
          </button>
        </div>
      </div>
    </div>
  );
}
