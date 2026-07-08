/**
 * In-memory auth state.
 * Access token stored in JS memory only (never localStorage).
 * Refresh token is HttpOnly cookie (handled by browser automatically).
 */
import { api, setAccessToken, clearAccessToken } from './api';

let _user = null;
let _inactivityTimer = null;
let _absoluteTimer = null;
let _warningTimer = null;
let _onInactivityWarning = null;
let _onForceLogout = null;

const INACTIVITY_MS = 30 * 60 * 1000;        // 30 minutes
const WARNING_BEFORE_MS = 2 * 60 * 1000;      // warn at 28 minutes
const ABSOLUTE_MS = 12 * 60 * 60 * 1000;     // 12 hours

export function getUser() { return _user; }
export function isLoggedIn() { return _user !== null; }

export function setCallbacks({ onWarning, onLogout }) {
  _onInactivityWarning = onWarning;
  _onForceLogout = onLogout;
}

export async function login(email, password) {
  const res = await api.post('/api/auth/login/', { email, password });
  if (!res.ok) throw new Error(res.data?.error || 'Login failed');
  if (res.data.requires_totp) {
    return { requiresTotp: true, partialToken: res.data.partial_token };
  }
  _finalizeLogin(res.data.access_token, res.data.user);
  return { requiresTotp: false };
}

export async function verifyTotp(partialToken, code) {
  const res = await api.post('/api/auth/totp/verify-login/', { partial_token: partialToken, code });
  if (!res.ok) throw new Error(res.data?.error || 'Invalid TOTP code');
  _finalizeLogin(res.data.access_token, res.data.user);
}

export async function useRecoveryCode(partialToken, recoveryCode) {
  const res = await api.post('/api/auth/totp/recovery/', { partial_token: partialToken, recovery_code: recoveryCode });
  if (!res.ok) throw new Error(res.data?.error || 'Invalid recovery code');
  _finalizeLogin(res.data.access_token, res.data.user);
}

export async function logout() {
  clearTimers();
  await api.post('/api/auth/logout/', {});
  _user = null;
  clearAccessToken();
  if (_onForceLogout) _onForceLogout('logout');
}

export async function refreshToken() {
  const res = await api.post('/api/auth/refresh/', {});
  if (!res.ok) {
    _user = null;
    clearAccessToken();
    if (_onForceLogout) _onForceLogout('expired');
    return false;
  }
  setAccessToken(res.data.access_token);
  return true;
}

function _finalizeLogin(accessToken, user) {
  setAccessToken(accessToken);
  _user = user;
  _startTimers();
}

function _startTimers() {
  clearTimers();
  _resetInactivity();

  _absoluteTimer = setTimeout(() => {
    logout();
    if (_onForceLogout) _onForceLogout('absolute_timeout');
  }, ABSOLUTE_MS);

  // Reset inactivity on user interaction
  ['mousemove', 'keydown', 'click', 'touchstart', 'scroll'].forEach(evt =>
    window.addEventListener(evt, _resetInactivity, { passive: true })
  );
}

function _resetInactivity() {
  clearTimeout(_inactivityTimer);
  clearTimeout(_warningTimer);

  _warningTimer = setTimeout(() => {
    if (_onInactivityWarning) _onInactivityWarning();
  }, INACTIVITY_MS - WARNING_BEFORE_MS);

  _inactivityTimer = setTimeout(() => {
    logout();
    if (_onForceLogout) _onForceLogout('inactivity');
  }, INACTIVITY_MS);
}

export function clearTimers() {
  clearTimeout(_inactivityTimer);
  clearTimeout(_absoluteTimer);
  clearTimeout(_warningTimer);
  ['mousemove', 'keydown', 'click', 'touchstart', 'scroll'].forEach(evt =>
    window.removeEventListener(evt, _resetInactivity)
  );
}