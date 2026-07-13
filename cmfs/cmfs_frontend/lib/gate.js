/**
 * FILE: cmfs/cmfs_frontend/lib/gate.js
 * ACTION: CREATE (Phase 8)
 *
 * Thin API wrappers only — the offline queue and cached delegate list
 * live in pages/gate/index.js's own React state (in memory, never
 * localStorage, per spec), not in this module.
 */
import { api } from './api';

/** GET /api/gate/{unitId}/delegates/ — full list + attendance state, for offline caching. */
export async function getGateDelegates(unitId) {
  return api.get(`/api/gate/${unitId}/delegates/`);
}

/** POST /api/gate/checkin/ — mark one delegate attended (online path). */
export async function checkinSingle(delegateId, timestamp) {
  return api.post('/api/gate/checkin/', { delegate_id: delegateId, timestamp });
}

/** POST /api/gate/checkin/batch/ — sync an offline attendance queue. records: [{delegate_id, timestamp}]. */
export async function checkinBatch(records) {
  return api.post('/api/gate/checkin/batch/', { records });
}

/** POST /api/gate/checkin/cash-payment/ — collect a balance at the gate + check in, atomically. Online only. */
export async function gateCashPayment(delegateId, amount, notes = '') {
  return api.post('/api/gate/checkin/cash-payment/', { delegate_id: delegateId, amount, notes });
}
