export const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

export function buildApiUrl(path) {
  return `${API_BASE}${path}`;
}

export function buildWebSocketUrl(path) {
  const resolvedPath = buildApiUrl(path);

  if (/^wss?:\/\//i.test(resolvedPath)) {
    return resolvedPath;
  }

  if (/^https?:\/\//i.test(resolvedPath)) {
    const url = new URL(resolvedPath);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    return url.toString();
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const pathname = resolvedPath.startsWith("/") ? resolvedPath : `/${resolvedPath}`;
  return `${protocol}//${window.location.host}${pathname}`;
}

export async function request(path, options = {}) {
  const response = await fetch(buildApiUrl(path), {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const raw = await response.text();
  let payload = null;

  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch {
      payload = raw;
    }
  }

  if (!response.ok) {
    const errorMessage =
      typeof payload === "string"
        ? payload
        : payload?.detail || `Request failed (${response.status})`;
    throw new Error(errorMessage);
  }

  return payload;
}
