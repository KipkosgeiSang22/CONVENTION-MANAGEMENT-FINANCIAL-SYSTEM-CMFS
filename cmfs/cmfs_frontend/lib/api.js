const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

let _accessToken = null;

export function setAccessToken(token) { _accessToken = token; }
export function clearAccessToken() { _accessToken = null; }

export async function apiFetch(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (_accessToken) headers['Authorization'] = `Bearer ${_accessToken}`;

  const response = await fetch(url, { ...options, headers, credentials: 'include' });
  let data;
  try { data = await response.json(); } catch { data = null; }
  return { ok: response.ok, status: response.status, data };
}

export async function apiFetchBlob(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const headers = { ...(options.headers || {}) };
  if (_accessToken) headers['Authorization'] = `Bearer ${_accessToken}`;

  const response = await fetch(url, { ...options, headers, credentials: 'include' });
  if (!response.ok) {
    let data;
    try { data = await response.json(); } catch { data = null; }
    return { ok: false, status: response.status, data };
  }
  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="?([^"]+)"?/);
  return { ok: true, status: response.status, blob, filename: match ? match[1] : null };
}

export const api = {
  get:   (path, opts = {}) => apiFetch(path, { ...opts, method: 'GET' }),
  post:  (path, body, opts = {}) => apiFetch(path, { ...opts, method: 'POST', body: JSON.stringify(body) }),
  patch: (path, body, opts = {}) => apiFetch(path, { ...opts, method: 'PATCH', body: JSON.stringify(body) }),
  del:   (path, opts = {}) => apiFetch(path, { ...opts, method: 'DELETE' }),
};

export async function checkHealth() {
  return api.get('/api/health/');
}