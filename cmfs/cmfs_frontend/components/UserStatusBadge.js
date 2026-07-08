/**
 * FILE: cmfs/cmfs_frontend/components/UserStatusBadge.js
 * ACTION: NEW (Phase 4)
 *
 * Pill badge rendering a user's derived status.
 * Status values: 'active' | 'pending_setup' | 'locked'
 */

const STATUS_CONFIG = {
  active: {
    label: 'Active',
    className: 'bg-green-100 text-green-700 border border-green-200',
  },
  pending_setup: {
    label: 'Pending Setup',
    className: 'bg-amber-100 text-amber-700 border border-amber-200',
  },
  locked: {
    label: 'Locked',
    className: 'bg-red-100 text-red-700 border border-red-200',
  },
};

export default function UserStatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || {
    label: status || 'Unknown',
    className: 'bg-gray-100 text-gray-600 border border-gray-200',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
}