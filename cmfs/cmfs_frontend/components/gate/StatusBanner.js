/**
 * FILE: cmfs/cmfs_frontend/components/gate/StatusBanner.js
 * ACTION: CREATE (Phase 8)
 *
 * Always-visible, non-dismissable banner (no close button, ever — the
 * whole point is the Gate Official can't accidentally hide it). Exactly
 * one of 5 states is shown at any time:
 *   RED    — offline
 *   AMBER  — online, but unsynced records are queued
 *   GREEN  — online, fully synced
 *   TICK   — a scan/check-in just succeeded (brief, replaced on next state change)
 *   ERROR  — something failed and needs attention (failed syncs, load errors)
 */
const STYLES = {
  RED:   { bg: 'bg-red-600',    text: 'text-white' },
  AMBER: { bg: 'bg-amber-500',  text: 'text-white' },
  GREEN: { bg: 'bg-green-600',  text: 'text-white' },
  TICK:  { bg: 'bg-blue-600',   text: 'text-white' },
  ERROR: { bg: 'bg-red-800',    text: 'text-white' },
};

export default function StatusBanner({ state, message }) {
  const style = STYLES[state] || STYLES.ERROR;
  return (
    <div className={`${style.bg} ${style.text} px-4 py-2 text-sm font-medium flex items-center justify-center gap-2 text-center`}>
      <span>{message}</span>
    </div>
  );
}
