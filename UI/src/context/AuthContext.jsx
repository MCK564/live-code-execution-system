/**
 * AuthContext.jsx
 * ---------------------------------------------------------------------------
 * Global auth state provider.
 *
 * Lifecycle:
 *  1. On mount → tries POST /api/auth/refresh (silent login using HttpOnly cookie).
 *     If the cookie is still valid, the user is restored without a login page.
 *  2. login(token, expiresIn) → stores token in memory, decodes user from JWT,
 *     schedules an auto-refresh 90 s before expiry.
 *  3. logout() → clears memory token, user state, and any timers.
 *  4. Registers refresh() in authStore so client.js can call it on 401.
 *  5. Listens for the auth:logout custom event dispatched by client.js.
 * ---------------------------------------------------------------------------
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { refreshToken } from "../api/authClient";
import { clearToken, setRefreshFn, setToken } from "../lib/authStore";

const AuthContext = createContext(null);

/** Decode JWT payload without verifying signature (display-only). */
function parseJwt(token) {
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(base64));
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  /** Decoded JWT claims — { sub, email, name, picture, provider, exp, … } */
  const [user, setUser] = useState(null);
  /** True while we are attempting the initial silent refresh on app load. */
  const [isLoading, setIsLoading] = useState(true);

  const refreshTimerRef = useRef(null);

  // ── scheduleAutoRefresh ─────────────────────────────────────────────────
  const scheduleAutoRefresh = useCallback(
    (expiresIn) => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
      // Fire 90 s before the access token expires; at least 5 s from now
      const delay = Math.max((expiresIn - 90) * 1000, 5_000);
      refreshTimerRef.current = setTimeout(async () => {
        try {
          await refresh(); // eslint-disable-line no-use-before-define
        } catch {
          logout(); // eslint-disable-line no-use-before-define
        }
      }, delay);
    },
    [] // refresh / logout added below via ref to avoid stale closures
  );

  // ── login ───────────────────────────────────────────────────────────────
  const login = useCallback(
    (accessToken, expiresIn) => {
      setToken(accessToken, expiresIn);
      const claims = parseJwt(accessToken);
      setUser(claims);
      scheduleAutoRefresh(expiresIn);
    },
    [scheduleAutoRefresh]
  );

  // ── logout ──────────────────────────────────────────────────────────────
  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
  }, []);

  // ── refresh ─────────────────────────────────────────────────────────────
  const refresh = useCallback(async () => {
    const data = await refreshToken(); // POST /api/auth/refresh (cookie sent auto)
    login(data.access_token, data.expires_in);
    return data;
  }, [login]);

  // Register refresh fn so client.js can call triggerRefresh() on 401
  useEffect(() => {
    setRefreshFn(refresh);
    return () => setRefreshFn(null);
  }, [refresh]);

  // Silent login on page load
  useEffect(() => {
    if (typeof window !== "undefined" && window.location.pathname === "/login/success") {
      setIsLoading(false);
      return undefined;
    }

    let cancelled = false;
    (async () => {
      try {
        await refresh();
      } catch {
        // No valid session — user will be redirected to /login by ProtectedRoute
        logout();
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Listen for forced-logout events from client.js (unrecoverable 401)
  useEffect(() => {
    const handler = () => {
      logout();
      // Navigation is handled by ProtectedRoute detecting isAuthenticated=false
    };
    window.addEventListener("auth:logout", handler);
    return () => window.removeEventListener("auth:logout", handler);
  }, [logout]);

  // Cleanup timer on unmount
  useEffect(
    () => () => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    },
    []
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refresh,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>.");
  return ctx;
}
