// FILE: cmfs/cmfs_frontend/lib/dashboard.js
// ACTION: CREATE (Phase 11)

import { api } from './api';

// Shape of the response depends on the caller's role — see
// reports/dashboard_views.py for the exact per-role payload.
export async function getDashboard() {
  return api.get('/api/dashboard/');
}
