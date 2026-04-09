/**
 * DashboardPage.jsx
 * ---------------------------------------------------------------------------
 * Protected page at /dashboard.
 * Shows the authenticated user's profile decoded from the JWT access token
 * (email, name, avatar, provider).
 *
 * No /users/me endpoint is called — all user info is already embedded in the
 * JWT payload by the backend during the callback flow.
 * ---------------------------------------------------------------------------
 */

import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// ── Avatar ─────────────────────────────────────────────────────────────────

function Avatar({ src, name }) {
  if (src) {
    return (
      <img
        src={src}
        alt={name ?? "User avatar"}
        referrerPolicy="no-referrer"
        className="h-24 w-24 rounded-2xl object-cover shadow-xl ring-2 ring-slate-700 ring-offset-4 ring-offset-slate-900"
      />
    );
  }

  const initials = (name ?? "?")
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="flex h-24 w-24 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-amber-600 text-2xl font-bold text-ink shadow-xl shadow-amber-500/30 ring-2 ring-slate-700 ring-offset-4 ring-offset-slate-900">
      {initials}
    </div>
  );
}

// ── InfoCard ───────────────────────────────────────────────────────────────

function InfoCard({ label, value, mono = false }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
      <p className="mb-1 text-[10px] font-medium uppercase tracking-widest text-slate-600">
        {label}
      </p>
      <p
        className={`truncate text-sm text-slate-300 ${
          mono ? "font-mono" : "font-medium"
        }`}
        title={value}
      >
        {value ?? "—"}
      </p>
    </div>
  );
}

// ── Navbar ─────────────────────────────────────────────────────────────────

function Navbar({ onLogout }) {
  const navigate = useNavigate();
  return (
    <header className="relative z-10 border-b border-slate-800/60 bg-slate-900/70 px-6 py-4 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between">
        {/* Brand */}
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2.5 transition-opacity hover:opacity-80"
          aria-label="Go to workspace"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 shadow shadow-amber-600/30">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
              className="h-4 w-4 text-ink"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5"
              />
            </svg>
          </div>
          <span className="font-bold text-slate-100">LiveCode</span>
        </button>

        {/* Nav actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate("/")}
            className="hidden items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800/60 px-3 py-1.5 text-xs font-medium text-slate-300 transition-all hover:border-slate-600 hover:text-white sm:flex"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="h-3.5 w-3.5"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5"
              />
            </svg>
            Workspace
          </button>

          <button
            id="btn-logout"
            onClick={onLogout}
            className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800/60 px-3 py-1.5 text-xs font-medium text-slate-400 transition-all hover:border-red-900/60 hover:bg-red-950/30 hover:text-red-400 active:scale-95"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="h-3.5 w-3.5"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75"
              />
            </svg>
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  // Derive sub-id (e.g. "google:12345678" → "12345678")
  const shortId = user?.sub?.includes(":")
    ? user.sub.split(":").slice(1).join(":")
    : (user?.sub ?? "");

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-ink via-slate-950 to-slate-900 text-slate-100">
      {/* Background */}
      <div className="pointer-events-none fixed inset-0 bg-grid-fade bg-[size:36px_36px] opacity-20" />
      <div className="pointer-events-none fixed left-1/2 top-0 h-96 w-96 -translate-x-1/2 rounded-full bg-amber-500/5 blur-3xl" />

      {/* Nav */}
      <Navbar onLogout={handleLogout} />

      {/* Content */}
      <main className="relative z-10 flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-lg animate-fade-in space-y-4">

          {/* ── Profile card ── */}
          <div className="relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/90 p-8 shadow-glass backdrop-blur">
            {/* Header glow */}
            <div className="absolute -top-24 left-1/2 h-48 w-48 -translate-x-1/2 rounded-full bg-amber-500/8 blur-3xl" />

            {/* Avatar + name */}
            <div className="relative flex flex-col items-center text-center">
              <Avatar src={user?.picture} name={user?.name} />

              {/* Provider badge */}
              <div className="mt-4 inline-flex items-center gap-1.5 rounded-full border border-emerald-800/40 bg-emerald-950/40 px-2.5 py-1 text-xs font-medium text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" aria-hidden="true" />
                Authenticated via {user?.provider ?? "OAuth2"}
              </div>

              <h2 className="mt-3 text-xl font-bold text-slate-100">
                {user?.name ?? "Welcome!"}
              </h2>
              <p className="mt-1 font-mono text-sm text-slate-400">
                {user?.email ?? ""}
              </p>
            </div>

            {/* Divider */}
            <div className="my-7 h-px w-full bg-gradient-to-r from-transparent via-slate-800 to-transparent" />

            {/* CTA buttons */}
            <div className="flex flex-col gap-3">
              <button
                id="btn-open-workspace"
                onClick={() => navigate("/")}
                className="group flex w-full items-center justify-center gap-2.5 rounded-2xl bg-gradient-to-r from-amber-500 to-amber-600 px-6 py-3.5 text-sm font-semibold text-ink shadow-lg shadow-amber-500/25 transition-all duration-200 hover:from-amber-400 hover:to-amber-500 hover:shadow-amber-500/40 active:scale-[0.98]"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                  className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-0.5"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5"
                  />
                </svg>
                Open Workspace
              </button>

              <button
                onClick={handleLogout}
                className="flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-700 bg-slate-800/40 px-6 py-3 text-sm font-medium text-slate-400 transition-all hover:border-red-900/50 hover:bg-red-950/20 hover:text-red-400 active:scale-[0.98]"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                  className="h-4 w-4"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75"
                  />
                </svg>
                Sign out
              </button>
            </div>
          </div>

          {/* ── Info grid ── */}
          <div className="grid grid-cols-2 gap-3">
            <InfoCard label="Email" value={user?.email} />
            <InfoCard label="Provider" value={user?.provider} />
            <InfoCard label="User ID" value={shortId} mono />
            <InfoCard
              label="Token status"
              value="Active ✓"
            />
          </div>

          {/* ── Security note ── */}
          <div className="flex items-start gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-3.5">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-xs leading-relaxed text-slate-500">
              Your{" "}
              <span className="font-medium text-slate-400">access token</span>{" "}
              lives in memory only and is auto-refreshed. The{" "}
              <span className="font-medium text-slate-400">
                refresh token
              </span>{" "}
              is stored as an HttpOnly cookie, invisible to JavaScript.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
