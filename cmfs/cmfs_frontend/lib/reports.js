import { api, apiFetchBlob } from './api';

export async function listReports(conventionId) {
  return api.get(`/api/reports/convention/${conventionId}/`);
}

export async function listUnitReports(unitId) {
  return api.get(`/api/reports/unit/${unitId}/`);
}

export async function getReport(reportId) {
  return api.get(`/api/reports/${reportId}/`);
}

// Fetches the file as a blob (auth header attached — the JWT lives only in
// memory, so a plain <a href> link can't carry it) and triggers a normal
// browser save via a temporary object URL. Never navigates the user away.
export async function downloadReport(reportId) {
  const res = await apiFetchBlob(`/api/reports/${reportId}/download/`);
  if (!res.ok) return res;

  const url = window.URL.createObjectURL(res.blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = res.filename || `report-${reportId}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
  return res;
}

// DEV/TESTING CONVENIENCE ONLY — generates the full report set on demand,
// at any convention status, without going through financial close.
// Restricted server-side to Super Admin.
export async function devGenerateReports(conventionId, reportType = 'final') {
  return api.post(`/api/reports/dev-generate/${conventionId}/`, { report_type: reportType });
}

// ── Annual Summary (Phase 11, Super Admin only) ─────────────────────────────

export async function listAnnualSummaries() {
  return api.get('/api/reports/annual-summary/');
}

export async function downloadAnnualSummary(year, format = 'xlsx') {
  const res = await apiFetchBlob(`/api/reports/annual-summary/${year}/download/?format=${format}`);
  if (!res.ok) return res;

  const url = window.URL.createObjectURL(res.blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = res.filename || `annual-summary-${year}.${format}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
  return res;
}

// DEV/TESTING CONVENIENCE ONLY — generates the annual summary for a given
// year on demand, without waiting for the automatic 7-days-after-December-
// close trigger. Restricted server-side to Super Admin.
export async function devGenerateAnnualSummary(year) {
  return api.post(`/api/reports/annual-summary/dev-generate/${year}/`, {});
}
