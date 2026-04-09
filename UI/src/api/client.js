/**
 * client.js  (updated)
 * ---------------------------------------------------------------------------
 * General API client for all code-session / execution / analyzer calls.
 * - Automatically attaches Authorization: Bearer <token> from memory store.
 * - On 401: triggers a token refresh via authStore, retries once.
 * - On refresh failure: dispatches auth:logout event → AuthProvider reacts.
 * ---------------------------------------------------------------------------
 */

import {
  getAccessToken,
  isTokenExpired,
  triggerRefresh,
} from "../lib/authStore";

export const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

export function buildApiUrl(path) {
  return `${API_BASE}${path}`;
}

export function buildWebSocketUrl(path) {
  const resolvedPath = buildApiUrl(path);

  if (/^wss?:\/\//i.test(resolvedPath)) return resolvedPath;

  if (/^https?:\/\//i.test(resolvedPath)) {
    const url = new URL(resolvedPath);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    return url.toString();
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const pathname = resolvedPath.startsWith("/") ? resolvedPath : `/${resolvedPath}`;
  return `${protocol}//${window.location.host}${pathname}`;
}

function buildHeaders(extra = {}) {
  const token = getAccessToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

async function parseResponse(res) {
  const raw = await res.text();
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

function extractErrorMessage(payload, status) {
  if (typeof payload === "string") return payload;
  return payload?.detail ?? `Request failed (${status})`;
}

export async function request(path, options = {}) {
  // Pre-emptively refresh if token expires within 60 s
  if (getAccessToken() && isTokenExpired()) {
    try {
      await triggerRefresh();
    } catch {
      // Will surface as 401 after the real request, handled below
    }
  }

  const headers = buildHeaders(options.headers ?? {});

  const response = await fetch(buildApiUrl(path), {
    credentials: "include",
    ...options,
    headers,
  });

  // ── Happy path ─────────────────────────────────────────────────────────
  if (response.ok) {
    return parseResponse(response);
  }

  // ── 401: attempt one silent refresh then retry ─────────────────────────
  if (response.status === 401) {
    try {
      await triggerRefresh();
    } catch {
      // Refresh itself failed — force logout
      window.dispatchEvent(new CustomEvent("auth:logout"));
      throw new Error("Session expired. Please log in again.");
    }

    const retryResponse = await fetch(buildApiUrl(path), {
      credentials: "include",
      ...options,
      headers: buildHeaders(options.headers ?? {}),
    });

    const retryPayload = await parseResponse(retryResponse);

    if (!retryResponse.ok) {
      throw new Error(extractErrorMessage(retryPayload, retryResponse.status));
    }

    return retryPayload;
  }

  // ── Other error ────────────────────────────────────────────────────────
  const payload = await parseResponse(response);
  throw new Error(extractErrorMessage(payload, response.status));
}
