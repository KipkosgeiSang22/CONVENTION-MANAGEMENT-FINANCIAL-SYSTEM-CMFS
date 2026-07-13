/**
 * FILE: cmfs/cmfs_frontend/components/gate/LogoutWarningModal.js
 * ACTION: CREATE (Phase 8)
 *
 * Shown when the Gate Official tries to log out with a non-empty
 * offline queue — logging out would lose those records, since the
 * queue lives in memory only (never localStorage). Cancel is the
 * default/focused button so an accidental Enter/tap doesn't wipe it.
 */
export default function LogoutWarningModal({ queueCount, onCancel, onConfirm }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 text-center">
        <p className="text-4xl mb-3">⚠️</p>
        <h3 className="text-lg font-bold text-gray-900 mb-2">Unsynced check-ins will be lost</h3>
        <p className="text-sm text-gray-500 mb-6">
          You have <strong>{queueCount}</strong> unsynced attendance record{queueCount !== 1 ? 's' : ''} still
          on this device. Logging out now will lose {queueCount !== 1 ? 'them' : 'it'} — reconnect and let them
          sync first if possible.
        </p>
        <div className="flex gap-3">
          <button
            autoFocus
            onClick={onCancel}
            className="flex-1 bg-blue-600 text-white rounded-lg py-2.5 text-sm font-semibold hover:bg-blue-700"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 border border-red-300 text-red-600 rounded-lg py-2.5 text-sm font-medium hover:bg-red-50"
          >
            Log Out Anyway
          </button>
        </div>
      </div>
    </div>
  );
}
