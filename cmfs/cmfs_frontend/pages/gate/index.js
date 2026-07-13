/**
 * FILE: cmfs/cmfs_frontend/pages/gate/index.js
 * ACTION: CREATE (Phase 8)
 *
 * Gate Official's scanning app. Loads the full delegate list into memory
 * at login, resolves every scan against that in-memory list (never a
 * per-scan server round trip), and queues attendance records locally
 * (in React state, never localStorage) while offline, syncing them one
 * batch at a time once connectivity returns.
 *
 * Deliberately NOT wrapped in <InactivityGuard> — that component force-
 * logs-out via a hard `window.location` navigation, which would silently
 * wipe an unsynced offline queue with no warning. A Gate Official is
 * also continuously interacting with the screen during active use, so
 * inactivity timeout has little value here anyway.
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { useRouter } from 'next/router';
import useAuth from '../../lib/useAuth';
import { logout } from '../../lib/auth';
import { getMyUnits } from '../../lib/budget';
import { getGateDelegates, checkinSingle, checkinBatch, gateCashPayment } from '../../lib/gate';
import QrScanner from '../../components/gate/QrScanner';
import StatusBanner from '../../components/gate/StatusBanner';
import ScanResultModal from '../../components/gate/ScanResultModal';
import CashPaymentForm from '../../components/gate/CashPaymentForm';
import LogoutWarningModal from '../../components/gate/LogoutWarningModal';

const ALLOWED_ROLES = ['gate_official', 'super_admin', 'national_head', 'regional_head', 'county_head'];
const HEALTH_CHECK_INTERVAL_MS = 10000;
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function GateCheckInPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const [units, setUnits] = useState(null);
  const [unitId, setUnitId] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [loadingDelegates, setLoadingDelegates] = useState(false);

  const [delegates, setDelegates] = useState({});   // { [delegate_id]: delegateObj }
  const delegatesRef = useRef({});
  const [syncedAt, setSyncedAt] = useState(null);
  const [total, setTotal] = useState(0);

  const [online, setOnline] = useState(true);
  const onlineRef = useRef(true);

  const [queue, setQueue] = useState([]);           // [{delegate_id, timestamp}]
  const queueRef = useRef([]);
  const [failedRecords, setFailedRecords] = useState([]);
  const [syncing, setSyncing] = useState(false);

  const [scanResult, setScanResult] = useState(null);
  const [cashDelegate, setCashDelegate] = useState(null);
  const [marking, setMarking] = useState(false);
  const [cashSubmitting, setCashSubmitting] = useState(false);
  const [tick, setTick] = useState(false);
  const [showLogoutWarning, setShowLogoutWarning] = useState(false);
  const [view, setView] = useState('scan'); // 'scan' | 'roster' — roster reads straight from the in-memory list, no extra request, works offline too

  // ── Role guard ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (!authLoading && user && !ALLOWED_ROLES.includes(user.role)) {
      router.replace('/dashboard');
    }
  }, [authLoading, user, router]);

  // ── Resolve convention unit (same pattern as Budget/Delegates modules) ──
  useEffect(() => {
    if (!user) return;
    (async () => {
      const res = await getMyUnits();
      if (res.ok) {
        setUnits(res.data);
        if (res.data.length === 1) setUnitId(res.data[0].unit_id);
      } else {
        setLoadError(res.data?.error || 'Failed to resolve your convention unit.');
      }
    })();
  }, [user]);

  // ── Load delegate list once the unit is known ───────────────────────────
  const loadDelegates = useCallback(async () => {
    if (!unitId) return;
    setLoadingDelegates(true);
    setLoadError('');
    const res = await getGateDelegates(unitId);
    setLoadingDelegates(false);
    if (!res.ok) { setLoadError(res.data?.error || 'Failed to load delegate list.'); return; }
    const map = {};
    (res.data.delegates || []).forEach(d => { map[d.delegate_id] = d; });
    setDelegates(map);
    delegatesRef.current = map;
    setSyncedAt(res.data.synced_at);
    setTotal(res.data.total || 0);
  }, [unitId]);

  useEffect(() => { loadDelegates(); }, [loadDelegates]);

  // ── Sync offline queue ───────────────────────────────────────────────────
  // Defined fresh every render (closes over the current `user`), but always
  // invoked through syncQueueRef (see below) so the connectivity poller —
  // set up once on mount — never calls a stale version of it.
  async function syncQueue() {
    if (queueRef.current.length === 0) return;
    setSyncing(true);
    const records = [...queueRef.current];
    const res = await checkinBatch(records);
    setSyncing(false);

    if (!res.ok) return; // connection dropped mid-sync; retried on next health check

    const results = res.data.results || [];
    const stillFailed = [];
    const succeededIds = new Set();

    results.forEach((r, i) => {
      if (r.success) succeededIds.add(records[i].delegate_id);
      else stillFailed.push({ ...records[i], error: r.error });
    });

    const remaining = queueRef.current.filter(r => !succeededIds.has(r.delegate_id));
    queueRef.current = remaining;
    setQueue(remaining);
    if (stillFailed.length > 0) setFailedRecords(prev => [...prev, ...stillFailed]);

    const updatedMap = { ...delegatesRef.current };
    results.forEach((r, i) => {
      if (r.success && updatedMap[records[i].delegate_id]) {
        updatedMap[records[i].delegate_id] = {
          ...updatedMap[records[i].delegate_id],
          checked_in: true,
          checked_in_at: r.checked_in_at || records[i].timestamp,
          checked_in_by_name: r.checked_in_by_name || user?.full_name || '',
        };
      }
    });
    delegatesRef.current = updatedMap;
    setDelegates(updatedMap);
  }

  const syncQueueRef = useRef(syncQueue);
  useEffect(() => { syncQueueRef.current = syncQueue; });

  // ── Connectivity polling (10s) — set up once, reads everything via refs ──
  useEffect(() => {
    let cancelled = false;

    async function checkOnline() {
      let isOnline = false;
      try {
        const res = await fetch(`${API_BASE_URL}/api/health/`, { cache: 'no-store' });
        isOnline = res.ok;
      } catch {
        isOnline = false;
      }
      if (cancelled) return;
      const wasOffline = !onlineRef.current;
      onlineRef.current = isOnline;
      setOnline(isOnline);
      if (isOnline && wasOffline && queueRef.current.length > 0) {
        syncQueueRef.current();
      }
    }

    checkOnline();
    const interval = setInterval(checkOnline, HEALTH_CHECK_INTERVAL_MS);
    window.addEventListener('online', checkOnline);
    window.addEventListener('offline', checkOnline);
    return () => {
      cancelled = true;
      clearInterval(interval);
      window.removeEventListener('online', checkOnline);
      window.removeEventListener('offline', checkOnline);
    };
  }, []);

  // ── Scan handling ────────────────────────────────────────────────────────
  function handleScan(rawText) {
    const delegateId = rawText.trim();
    const delegate = delegatesRef.current[delegateId];

    if (!delegate) {
      setScanResult({ type: onlineRef.current ? 'not_found_online' : 'not_found_offline' });
      return;
    }
    if (delegate.checked_in) {
      setScanResult({ type: 'already', delegate });
      return;
    }
    if (delegate.payment_status === 'COMPLETE' || delegate.payment_status === 'OVERPAID') {
      setScanResult({ type: 'complete', delegate });
      return;
    }
    setScanResult({ type: 'incomplete', delegate });
  }

  function closeScanResult() { setScanResult(null); }

  function queueOffline(delegateId, timestamp) {
    const next = [...queueRef.current, { delegate_id: delegateId, timestamp }];
    queueRef.current = next;
    setQueue(next);
  }

  function applyLocalCheckin(delegateId, checkedInAt, checkedInByName) {
    const updated = {
      ...delegatesRef.current,
      [delegateId]: {
        ...delegatesRef.current[delegateId],
        checked_in: true,
        checked_in_at: checkedInAt,
        checked_in_by_name: checkedInByName,
      },
    };
    delegatesRef.current = updated;
    setDelegates(updated);
  }

  function flashTick() {
    setTick(true);
    setTimeout(() => setTick(false), 2500);
  }

  // ── Mark as attended (COMPLETE payment path) ────────────────────────────
  async function handleMarkAttended(delegate) {
    setMarking(true);
    const timestamp = new Date().toISOString();

    if (onlineRef.current) {
      const res = await checkinSingle(delegate.delegate_id, timestamp);
      setMarking(false);
      if (res.ok) {
        applyLocalCheckin(delegate.delegate_id, res.data.checked_in_at || timestamp, res.data.checked_in_by_name || user.full_name);
        flashTick();
        setScanResult(null);
        return;
      }
      // Request failed mid-flight (connection dropped) — don't lose the
      // scan, fall through and queue it exactly like an offline one.
    }

    queueOffline(delegate.delegate_id, timestamp);
    applyLocalCheckin(delegate.delegate_id, timestamp, user.full_name);
    setMarking(false);
    setScanResult(null);
  }

  // ── Cash payment (INCOMPLETE payment path, online only) ─────────────────
  function handleOpenCashPayment(delegate) {
    setScanResult(null);
    setCashDelegate(delegate);
  }

  async function handleSubmitCashPayment(delegate, amount, notes) {
    setCashSubmitting(true);
    const res = await gateCashPayment(delegate.delegate_id, amount, notes);
    setCashSubmitting(false);
    if (!res.ok) {
      alert(res.data?.error || 'Could not record the payment. Try again.');
      return;
    }
    const updated = {
      ...delegatesRef.current,
      [delegate.delegate_id]: {
        ...delegatesRef.current[delegate.delegate_id],
        payment_status: res.data.payment_status,
        balance_owed: res.data.balance_owed,
        checked_in: true,
        checked_in_at: res.data.checked_in_at,
        checked_in_by_name: user.full_name,
      },
    };
    delegatesRef.current = updated;
    setDelegates(updated);
    setCashDelegate(null);
    flashTick();
  }

  // ── Logout ───────────────────────────────────────────────────────────────
  function handleLogoutClick() {
    if (queue.length > 0) { setShowLogoutWarning(true); return; }
    doLogout();
  }
  async function doLogout() {
    await logout();
    router.replace('/auth/login');
  }

  // ── Banner state (exactly one of 5, always, never dismissable) ──────────
  let bannerState = 'GREEN';
  let bannerMessage = `${total} delegates loaded. Last synced: ${syncedAt ? new Date(syncedAt).toLocaleTimeString('en-KE') : '—'}`;
  if (!online) {
    bannerState = 'RED';
    bannerMessage = `Offline — working from local list. ${queue.length} unsynced record${queue.length !== 1 ? 's' : ''}.`;
  } else if (failedRecords.length > 0) {
    bannerState = 'ERROR';
    bannerMessage = `${failedRecords.length} record(s) failed to sync — check with a Super Admin.`;
  } else if (queue.length > 0) {
    bannerState = 'AMBER';
    bannerMessage = `Online — syncing ${queue.length} unsynced record${queue.length !== 1 ? 's' : ''}…`;
  } else if (tick) {
    bannerState = 'TICK';
    bannerMessage = 'Checked in ✓';
  }

  // ── Render guards ─────────────────────────────────────────────────────────
  if (authLoading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (units && units.length > 1 && !unitId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="bg-white border border-gray-200 rounded-xl p-6 max-w-sm w-full">
          <h2 className="text-lg font-bold text-gray-900 mb-3">Choose your convention</h2>
          <select
            onChange={e => setUnitId(Number(e.target.value))}
            defaultValue=""
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="" disabled>Select…</option>
            {units.map(u => (
              <option key={u.unit_id} value={u.unit_id}>{u.convention_name} — {u.display_name}</option>
            ))}
          </select>
        </div>
      </div>
    );
  }

  if (units && units.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 text-center">
        <p className="text-gray-500">No convention is currently assigned to you.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <StatusBanner state={bannerState} message={bannerMessage} />

      <header className="bg-white border-b border-gray-200 px-4 py-3 flex justify-between items-center">
        <div>
          <p className="text-sm font-semibold text-gray-900">Gate Check-In</p>
          <p className="text-xs text-gray-400">{user.full_name}</p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => setView(v => (v === 'scan' ? 'roster' : 'scan'))}
            className="text-sm text-blue-600 hover:underline"
          >
            {view === 'scan' ? 'View All Delegates' : '← Back to Scanner'}
          </button>
          <button onClick={handleLogoutClick} className="text-sm text-red-600 hover:underline">
            Log Out
          </button>
        </div>
      </header>

      <main className="flex-1 px-4 py-6">
        {loadingDelegates ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-7 w-7 border-b-2 border-blue-600" />
          </div>
        ) : loadError ? (
          <div className="text-center py-16">
            <p className="text-red-500 text-sm mb-3">{loadError}</p>
            <button onClick={loadDelegates} className="text-blue-600 text-sm hover:underline">Retry</button>
          </div>
        ) : view === 'roster' ? (
          <DelegateRoster delegates={delegates} />
        ) : (
          <>
            <p className="text-center text-sm text-gray-500 mb-4">
              {total} delegates loaded. Last synced: {syncedAt ? new Date(syncedAt).toLocaleString('en-KE') : '—'}
            </p>
            <QrScanner onScan={handleScan} paused={!!scanResult || !!cashDelegate} />
            {queue.length > 0 && (
              <div className="max-w-sm mx-auto mt-4 bg-amber-50 border border-amber-200 text-amber-700 text-sm rounded-lg px-4 py-3 flex items-center justify-between">
                <span>{queue.length} unsynced record{queue.length !== 1 ? 's' : ''}</span>
                {online && (
                  <button onClick={syncQueue} disabled={syncing} className="text-xs font-medium underline disabled:opacity-50">
                    {syncing ? 'Syncing…' : 'Sync Now'}
                  </button>
                )}
              </div>
            )}
          </>
        )}
      </main>

      <ScanResultModal
        result={scanResult}
        online={online}
        onClose={closeScanResult}
        onMarkAttended={handleMarkAttended}
        onOpenCashPayment={handleOpenCashPayment}
        marking={marking}
      />

      {cashDelegate && (
        <CashPaymentForm
          delegate={cashDelegate}
          onCancel={() => setCashDelegate(null)}
          onSubmit={handleSubmitCashPayment}
          submitting={cashSubmitting}
        />
      )}

      {showLogoutWarning && (
        <LogoutWarningModal
          queueCount={queue.length}
          onCancel={() => setShowLogoutWarning(false)}
          onConfirm={doLogout}
        />
      )}
    </div>
  );
}

// ── Roster view — every loaded delegate, attended or not ────────────────────
//
// Reads straight from the in-memory delegate map already loaded for
// scanning (delegatesRef/delegates state) — no extra API call, and it
// still works while offline since it's the same local list a scan
// resolves against.
function DelegateRoster({ delegates }) {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all'); // all | attended | not_attended

  const all = Object.values(delegates);
  const attendedCount = all.filter(d => d.checked_in).length;

  const filtered = all
    .filter(d => {
      if (filter === 'attended') return !!d.checked_in;
      if (filter === 'not_attended') return !d.checked_in;
      return true;
    })
    .filter(d => {
      if (!search.trim()) return true;
      const q = search.trim().toLowerCase();
      return (
        (d.full_name || '').toLowerCase().includes(q) ||
        (d.delegate_id || '').toLowerCase().includes(q)
      );
    })
    .sort((a, b) => (a.full_name || '').localeCompare(b.full_name || ''));

  return (
    <div className="max-w-2xl mx-auto">
      <p className="text-center text-sm text-gray-500 mb-3">
        {attendedCount} of {all.length} delegates checked in
      </p>

      <input
        type="text"
        placeholder="Search by name or Delegate ID…"
        value={search}
        onChange={e => setSearch(e.target.value)}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-3"
      />

      <div className="flex gap-2 mb-4">
        {[
          { key: 'all', label: `All (${all.length})` },
          { key: 'attended', label: `Attended (${attendedCount})` },
          { key: 'not_attended', label: `Not Attended (${all.length - attendedCount})` },
        ].map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`text-xs px-3 py-1.5 rounded-full border ${
              filter === f.key
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-600 border-gray-300'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-100 max-h-[60vh] overflow-y-auto">
        {filtered.map(d => (
          <div key={d.delegate_id} className="px-4 py-2.5 flex items-center justify-between text-sm">
            <div>
              <p className="font-medium text-gray-900">{d.full_name}</p>
              <p className="text-xs text-gray-400 font-mono">{d.delegate_id}</p>
            </div>
            {d.checked_in ? (
              <span
                className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700"
                title={d.checked_in_at ? new Date(d.checked_in_at).toLocaleString('en-KE') : ''}
              >
                ✓ Checked In
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
                Not Yet
              </span>
            )}
          </div>
        ))}
        {filtered.length === 0 && (
          <p className="px-4 py-8 text-center text-gray-400 text-sm">No delegates match.</p>
        )}
      </div>
    </div>
  );
}
