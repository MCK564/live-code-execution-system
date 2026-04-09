/**
 * authClient.js
 * ---------------------------------------------------------------------------
 * Auth-specific API calls (code exchange, token refresh).
 * All requests go through the shared /api proxy → backend /auth/*.
 * credentials: "include" is required so the browser sends/stores
 * the HttpOnly refresh_token cookie automatically.
 * ---------------------------------------------------------------------------
 */

const AUTH_BASE = (import.meta.env.VITE_AUTH_BASE_URL ?? "/api/auth").replace(/\/$/, "");

async function authFetch(path, options = {}) {
  const res = await fetch(`${AUTH_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!res.ok) {
    let detail = `Auth request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* ignore parse error */
    }
    throw new Error(detail);
  }

  return res.json();
}

/**
 * Exchange a one-time code for an access_token.
 * The backend also sets the HttpOnly refresh_token cookie in this response.
 * @param {string} code  One-time code from /login/success?code=...
 * @returns {{ access_token: string, expires_in: number }}
 */
export async function exchangeCode(code) {
  return authFetch("/oauth2/exchange", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

/**
 * Use the HttpOnly refresh_token cookie to obtain a new access_token.
 * The browser sends the cookie automatically; no JS access needed.
 * @returns {{ access_token: string, expires_in: number }}
 */
export async function refreshToken() {
  return authFetch("/refresh", { method: "POST" });
}
