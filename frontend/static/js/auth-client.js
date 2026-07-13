/* BBLOTTO PRO V2 RC2 Sprint 2-1 로그인 유지 클라이언트 */
const BBAuth = (() => {
  const ACCESS = 'bblotto_access_token';
  const REFRESH = 'bblotto_refresh_token';
  const ADMIN = 'bblotto_admin';

  function setSession(data) {
    if (data.access_token) localStorage.setItem(ACCESS, data.access_token);
    if (data.refresh_token) localStorage.setItem(REFRESH, data.refresh_token);
    if (data.admin) localStorage.setItem(ADMIN, JSON.stringify(data.admin));
  }

  function clearSession() {
    localStorage.removeItem(ACCESS);
    localStorage.removeItem(REFRESH);
    localStorage.removeItem(ADMIN);
  }

  function accessToken() { return localStorage.getItem(ACCESS) || ''; }
  function refreshToken() { return localStorage.getItem(REFRESH) || ''; }
  function admin() {
    try { return JSON.parse(localStorage.getItem(ADMIN) || 'null'); }
    catch (_) { return null; }
  }

  async function login(username, password) {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    if (!res.ok) throw new Error((await res.json()).detail || '로그인 실패');
    const data = await res.json();
    setSession(data);
    return data;
  }

  async function refresh() {
    const token = refreshToken();
    if (!token) return null;
    const res = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: token })
    });
    if (!res.ok) { clearSession(); return null; }
    const data = await res.json();
    setSession(data);
    return data;
  }

  async function api(path, options = {}) {
    const headers = Object.assign({}, options.headers || {}, { Authorization: `Bearer ${accessToken()}` });
    let res = await fetch(path, Object.assign({}, options, { headers }));
    if (res.status === 401 && await refresh()) {
      const retryHeaders = Object.assign({}, options.headers || {}, { Authorization: `Bearer ${accessToken()}` });
      res = await fetch(path, Object.assign({}, options, { headers: retryHeaders }));
    }
    return res;
  }

  async function restore() {
    if (accessToken()) {
      const res = await api('/api/auth/me');
      if (res.ok) return await res.json();
    }
    const refreshed = await refresh();
    return refreshed ? refreshed.admin : null;
  }

  async function logout() {
    const token = refreshToken();
    try {
      if (token) await api('/api/auth/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: token })
      });
    } finally {
      clearSession();
    }
  }

  return { login, logout, restore, api, admin, accessToken, refreshToken, clearSession };
})();
