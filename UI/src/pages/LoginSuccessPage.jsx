/**
 * LoginSuccessPage.jsx
 * ---------------------------------------------------------------------------
 * Intermediate page at /login/success (the redirect target from the backend).
 *
 * Flow:
 *  1. Backend redirects here with ?code=ONE_TIME_CODE
 *  2. We call POST /api/auth/oauth2/exchange  { code }
 *  3. Backend returns { access_token, expires_in } + sets HttpOnly cookie
 *  4. We store token in memory via auth.login() and navigate to /dashboard
 *
 * On any failure we show an error and redirect back to /login after 3 s.
 * The `hasRun` ref prevents the exchange from running twice in React
 * Strict Mode (double-invoke in development).
 * ---------------------------------------------------------------------------
 */

import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { exchangeCode } from "../api/authClient";

// ── Spinner ────────────────────────────────────────────────────────────────

function ExchangeSpinner() {
  return (
    <div className="flex flex-col items-center gap-6 animate-fade-in">
      {/* Animated rings */}
      <div className="relative h-20 w-20">
        <div className="absolute inset-0 rounded-full border-2 border-slate-800" />
        <div className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-accent" />
        <div
          className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-r-amber-400/40"
          style={{ animationDuration: "1.8s", animationDirection: "reverse" }}
        />
        {/* Centre glow */}
        <div className="absolute inset-4 rounded-full bg-gradient-to-br from-amber-400/20 to-amber-600/10 shadow-lg shadow-amber-500/20" />
      </div>

      <div className="text-center">
        <p className="text-base font-semibold text-slate-200">Signing you in…</p>
        <p className="mt-1 font-mono text-xs text-slate-500">
          Exchanging authorization code
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {["Google Auth", "Exchange", "Session"].map((label, i) => (
          <div key={label} className="flex items-center gap-2">
            {i > 0 && (
              <div className="h-px w-6 bg-gradient-to-r from-accent/50 to-slate-700" />
            )}
            <div className="flex items-center gap-1.5">
              <div
                className={`h-1.5 w-1.5 rounded-full ${
                  i === 0
                    ? "bg-emerald-400"
                    : i === 1
                    ? "animate-pulse bg-accent"
                    : "bg-slate-700"
                }`}
              />
              <span className="text-[10px] font-mono text-slate-500">{label}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Error state ────────────────────────────────────────────────────────────

function ExchangeError({ message }) {
  return (
    <div className="flex flex-col items-center gap-5 animate-fade-in text-center">
      {/* Icon */}
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-red-500/30 bg-red-500/10">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          className="h-8 w-8 text-red-400"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
          />
        </svg>
      </div>

      <div>
        <p className="font-semibold text-slate-200">Authentication failed</p>
        <p className="mt-1.5 max-w-xs text-sm leading-relaxed text-slate-400">
          {message}
        </p>
      </div>

      <div className="flex items-center gap-2 font-mono text-xs text-slate-600">
        <div className="h-px w-8 bg-slate-800" />
        Redirecting to login
        <div className="h-px w-8 bg-slate-800" />
      </div>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function LoginSuccessPage() {
  const [searchParams] = useSearchParams();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [errorMsg, setErrorMsg] = useState("");
  const hasRun = useRef(false); // guard against Strict Mode double-invoke

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;

    const code = searchParams.get("code");

    if (!code) {
      setErrorMsg("No authorization code was found in the URL.");
      setTimeout(() => navigate("/login", { replace: true }), 3000);
      return;
    }

    exchangeCode(code)
      .then(({ access_token, expires_in }) => {
        login(access_token, expires_in);
        navigate("/dashboard", { replace: true });
      })
      .catch((err) => {
        setErrorMsg(
          err?.message ||
            "The code was invalid or has already been used. Please try again."
        );
        setTimeout(() => navigate("/login", { replace: true }), 3500);
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-b from-ink via-slate-950 to-slate-900 px-4">
      {/* Background */}
      <div className="pointer-events-none fixed inset-0 bg-grid-fade bg-[size:36px_36px] opacity-20" />
      <div className="pointer-events-none fixed left-1/2 top-1/2 h-96 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full bg-amber-500/5 blur-3xl" />

      {/* Card */}
      <div className="relative z-10 w-full max-w-sm">
        <div className="absolute -inset-px rounded-3xl bg-gradient-to-br from-amber-500/15 via-transparent to-blue-500/10 blur-xl" />
        <div className="relative rounded-3xl border border-slate-800 bg-slate-900/90 px-8 py-14 shadow-glass backdrop-blur">
          {errorMsg ? (
            <ExchangeError message={errorMsg} />
          ) : (
            <ExchangeSpinner />
          )}
        </div>
      </div>
    </div>
  );
}
