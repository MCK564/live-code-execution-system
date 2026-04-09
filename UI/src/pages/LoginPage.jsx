/**
 * LoginPage.jsx
 * ---------------------------------------------------------------------------
 * Public page at /login.
 * - If already authenticated, redirects straight to /dashboard.
 * - Clicking "Continue with Google" redirects the BROWSER (full page nav)
 *   through the shared /api proxy to the backend's Google OAuth2 authorize endpoint.
 *   The backend then redirects to Google → Google redirects to backend
 *   callback → backend redirects to /login/success?code=ONE_TIME_CODE.
 * ---------------------------------------------------------------------------
 */

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const AUTH_BASE = (
  import.meta.env.VITE_AUTH_BASE_URL ?? "/api/auth"
).replace(/\/$/, "");

// ── Icons ──────────────────────────────────────────────────────────────────

function GoogleIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M17.64 9.20443C17.64 8.56625 17.5827 7.95262 17.4764 7.36353H9V10.845H13.8436C13.635 11.97 13.0009 12.9232 12.0477 13.5614V15.8196H14.9564C16.6582 14.2527 17.64 11.9455 17.64 9.20443Z"
        fill="#4285F4"
      />
      <path
        d="M9 18C11.43 18 13.4673 17.1941 14.9564 15.8195L12.0477 13.5614C11.2418 14.1014 10.2109 14.4204 9 14.4204C6.65591 14.4204 4.67182 12.8372 3.96409 10.71H0.957272V13.0418C2.43818 15.9832 5.48182 18 9 18Z"
        fill="#34A853"
      />
      <path
        d="M3.96409 10.71C3.78409 10.17 3.68182 9.59313 3.68182 9C3.68182 8.40688 3.78409 7.83 3.96409 7.29V4.95818H0.957272C0.347727 6.17318 0 7.54773 0 9C0 10.4523 0.347727 11.8268 0.957272 13.0418L3.96409 10.71Z"
        fill="#FBBC05"
      />
      <path
        d="M9 3.57955C10.3214 3.57955 11.5077 4.03364 12.4405 4.92545L15.0218 2.34409C13.4632 0.891818 11.4259 0 9 0C5.48182 0 2.43818 2.01682 0.957272 4.95818L3.96409 7.29C4.67182 5.16273 6.65591 3.57955 9 3.57955Z"
        fill="#EA4335"
      />
    </svg>
  );
}

function LogoBracketIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={2}
      stroke="currentColor"
      className="h-7 w-7 text-ink"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5"
      />
    </svg>
  );
}

// ── Feature badge ──────────────────────────────────────────────────────────

function FeatureBadge({ label }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-700/60 bg-slate-800/60 px-3 py-1 text-xs text-slate-400">
      <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden="true" />
      {label}
    </span>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function LoginPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();

  // Redirect if already logged in
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate]);

  const handleGoogleLogin = () => {
    const redirectUri = `${window.location.origin}/login/success`;
    const authorizeUrl = new URL(
      `${window.location.origin}${AUTH_BASE}/oauth2/google/authorize`
    );
    authorizeUrl.searchParams.set("redirect_uri", redirectUri);
    window.location.href = authorizeUrl.toString();
  };

  return (
    <div className="relative flex min-h-screen overflow-hidden bg-gradient-to-b from-ink via-slate-950 to-slate-900 text-slate-100">
      {/* Background grid */}
      <div className="pointer-events-none fixed inset-0 bg-grid-fade bg-[size:36px_36px] opacity-25" />

      {/* Ambient glow orbs */}
      <div className="pointer-events-none fixed left-1/2 top-1/3 h-[28rem] w-[28rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-amber-500/5 blur-3xl" />
      <div className="pointer-events-none fixed bottom-1/4 left-1/4 h-64 w-64 rounded-full bg-blue-600/5 blur-3xl" />
      <div className="pointer-events-none fixed right-1/4 top-1/4 h-48 w-48 rounded-full bg-purple-600/5 blur-3xl" />

      {/* ── Left panel — branding ── */}
      <div className="relative z-10 hidden flex-1 flex-col items-start justify-center px-16 lg:flex xl:px-24">
        {/* Logo */}
        <div className="mb-10 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 shadow-lg shadow-amber-600/30">
            <LogoBracketIcon />
          </div>
          <span className="text-xl font-bold tracking-tight">LiveCode</span>
        </div>

        <h2 className="mb-4 max-w-sm text-4xl font-bold leading-tight tracking-tight text-slate-100">
          Code faster.{" "}
          <span className="bg-gradient-to-r from-amber-400 to-amber-600 bg-clip-text text-transparent">
            Ship smarter.
          </span>
        </h2>
        <p className="mb-10 max-w-xs text-base leading-relaxed text-slate-400">
          Run Python, Java, and C++ in isolated containers. Get real-time static
          analysis while you type.
        </p>

        {/* Feature badges */}
        <div className="flex flex-wrap gap-2">
          {[
            "Sandboxed Docker execution",
            "Real-time code analysis",
            "Multi-language support",
            "WebSocket-powered IDE",
          ].map((f) => (
            <FeatureBadge key={f} label={f} />
          ))}
        </div>

        {/* Decorative quote */}
        <div className="mt-16 max-w-xs rounded-2xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur">
          <p className="text-sm italic leading-relaxed text-slate-400">
            "Any fool can write code that a computer can understand. Good
            programmers write code that humans can understand."
          </p>
          <p className="mt-2 text-xs text-slate-600">— Martin Fowler</p>
        </div>
      </div>

      {/* ── Right panel — login card ── */}
      <div className="relative z-10 flex flex-1 items-center justify-center px-4 py-12 lg:max-w-md xl:max-w-lg">
        <div className="w-full max-w-sm animate-fade-in">
          {/* Glow ring */}
          <div className="absolute -inset-px rounded-3xl bg-gradient-to-br from-amber-500/20 via-transparent to-blue-500/10 blur-2xl" />

          <div className="relative rounded-3xl border border-slate-800 bg-slate-900/90 px-8 py-10 shadow-glass backdrop-blur">
            {/* Mobile logo */}
            <div className="mb-7 flex flex-col items-center text-center lg:hidden">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-amber-600 shadow-lg shadow-amber-600/30">
                <LogoBracketIcon />
              </div>
              <h1 className="text-xl font-bold text-slate-100">LiveCode</h1>
            </div>

            {/* Desktop heading */}
            <div className="mb-8 hidden lg:block">
              <h1 className="text-2xl font-bold text-slate-100">Welcome back</h1>
              <p className="mt-1.5 text-sm text-slate-400">
                Sign in to your workspace
              </p>
            </div>

            {/* Divider */}
            <div className="mb-7 h-px w-full bg-gradient-to-r from-transparent via-slate-800 to-transparent" />

            {/* Google button */}
            <button
              id="btn-google-login"
              onClick={handleGoogleLogin}
              className="group relative w-full flex items-center justify-center gap-3 rounded-2xl border border-slate-700 bg-slate-800/80 px-5 py-3.5 text-sm font-medium text-slate-200 shadow-sm transition-all duration-200 hover:border-slate-600 hover:bg-slate-700/80 hover:text-white hover:shadow-md active:scale-[0.97] focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50"
              aria-label="Sign in with Google"
            >
              {/* Shimmer on hover */}
              <span
                className="pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-r from-white/0 via-white/[0.04] to-white/0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
                aria-hidden="true"
              />
              <GoogleIcon />
              <span>Continue with Google</span>
              {/* Arrow nudge */}
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="ml-auto h-4 w-4 text-slate-500 transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-slate-300"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z"
                  clipRule="evenodd"
                />
              </svg>
            </button>

            {/* Security note */}
            <div className="mt-5 flex items-start gap-2 rounded-xl border border-slate-800 bg-slate-950/40 px-3.5 py-3">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z"
                  clipRule="evenodd"
                />
              </svg>
              <p className="text-xs leading-relaxed text-slate-500">
                Tokens are stored in{" "}
                <span className="font-medium text-slate-400">memory only</span>.
                Your refresh token is in an HttpOnly cookie — never exposed to
                JavaScript.
              </p>
            </div>

            {/* Terms */}
            <p className="mt-5 text-center text-xs text-slate-600">
              By continuing you agree to our{" "}
              <a
                href="#"
                className="text-slate-500 transition-colors hover:text-accent"
              >
                Terms
              </a>{" "}
              &{" "}
              <a
                href="#"
                className="text-slate-500 transition-colors hover:text-accent"
              >
                Privacy Policy
              </a>
            </p>
          </div>

          {/* Version watermark */}
          <p className="mt-6 text-center font-mono text-[10px] text-slate-700">
            LiveCode v1.0 · Google OAuth2
          </p>
        </div>
      </div>
    </div>
  );
}
