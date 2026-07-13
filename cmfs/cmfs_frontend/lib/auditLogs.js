// FILE: cmfs/cmfs_frontend/lib/auditLogs.js
// ACTION: CREATE (Phase 11)

import { api } from './api';

// filters: { user_id, action, date_from, date_to, page, page_size }
export async function listAuditLogs(filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') params.set(k, v);
  });
  const qs = params.toString();
  return api.get(`/api/audit-logs/${qs ? `?${qs}` : ''}`);
}
