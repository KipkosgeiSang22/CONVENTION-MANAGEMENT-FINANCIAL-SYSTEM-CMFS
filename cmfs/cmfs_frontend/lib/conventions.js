import { api } from './api';

export async function listConventions(params = {}) {
  const qs = new URLSearchParams();
  if (params.status) qs.set('status', params.status);
  if (params.page) qs.set('page', params.page);
  const query = qs.toString() ? `?${qs}` : '';
  return api.get(`/api/conventions/${query}`);
}

export async function getConvention(id) {
  return api.get(`/api/conventions/${id}/`);
}

export async function createConvention(body) {
  return api.post('/api/conventions/', body);
}

export async function updateConvention(id, body) {
  return api.patch(`/api/conventions/${id}/`, body);
}

export async function publishConvention(id) {
  return api.post(`/api/conventions/${id}/publish/`, {});
}

export async function activateConvention(id) {
  return api.post(`/api/conventions/${id}/activate/`, {});
}

export async function endConvention(id) {
  return api.post(`/api/conventions/${id}/end/`, {});
}

export async function closeConventionFinancially(id, totpCode) {
  return api.post(`/api/conventions/${id}/close/`, { totp_code: totpCode });
}

export async function archiveConvention(id) {
  return api.post(`/api/conventions/${id}/archive/`, {});
}

export async function triggerOpeningDayReports(id) {
  return api.post(`/api/conventions/${id}/opening-day-reports/`, {});
}

export async function listCounties() {
  return api.get('/api/conventions/counties/');
}

export async function listRegions() {
  return api.get('/api/conventions/regions/');
}

export const CONVENTION_STATUS = {
  DRAFT: 'draft', OPEN: 'open', ACTIVE: 'active',
  ENDED: 'ended', FINANCIALLY_CLOSED: 'financially_closed', ARCHIVED: 'archived',
};

export const STATUS_LABELS = {
  draft: 'Draft', open: 'Open', active: 'Active',
  ended: 'Ended', financially_closed: 'Financially Closed', archived: 'Archived',
};

export const STATUS_COLORS = {
  draft: 'bg-gray-100 text-gray-700',
  open: 'bg-blue-100 text-blue-700',
  active: 'bg-green-100 text-green-700',
  ended: 'bg-yellow-100 text-yellow-800',
  financially_closed: 'bg-purple-100 text-purple-700',
  archived: 'bg-gray-200 text-gray-500',
};

export function getAvailableTransitions(convention, userRole) {
  const transitions = [];
  const { status } = convention;
  const headRoles = ['super_admin', 'national_head', 'regional_head', 'county_head'];

  if (userRole === 'super_admin' && status === 'draft') {
    transitions.push({ label: 'Publish Convention', action: 'publish', variant: 'primary', confirm: true });
  }
  if (headRoles.includes(userRole) && status === 'open') {
      transitions.push({ label: 'Mark Active', action: 'activate', variant: 'success' });
    }
  if (headRoles.includes(userRole) && status === 'active') {
    transitions.push({ label: 'Generate Opening Day Reports', action: 'opening_reports', variant: 'info' });
    transitions.push({ label: 'End Convention', action: 'end', variant: 'warning' });
  }
  if (headRoles.includes(userRole) && status === 'ended') {
    transitions.push({ label: 'Generate Opening Day Reports', action: 'opening_reports', variant: 'info' });
    transitions.push({ label: 'Close Financially', action: 'close', variant: 'danger', requiresTotp: true });
  }
  if (userRole === 'super_admin' && status === 'financially_closed') {
    transitions.push({ label: 'Archive', action: 'archive', variant: 'secondary' });
  }
  return transitions;
}