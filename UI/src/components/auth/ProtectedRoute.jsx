/**
 * ProtectedRoute.jsx
 * ---------------------------------------------------------------------------
 * Wraps private routes. Shows a loading spinner while the initial silent
 * refresh is in progress (prevents flash-redirect to /login on hard reload).
 * ---------------------------------------------------------------------------
 */

import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

function FullPageSpinner() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-gradient-to-b from-ink via-slate-950 to-slate-900">
      <div className="pointer-events-none fixed inset-0 bg-grid-fade bg-[size:36px_36px] opacity-20" />
      <div className="relative z-10 flex flex-col items-center gap-4">
        <div className="relative h-12 w-12">
          {/* Outer ring */}
          <div className="absolute inset-0 rounded-full border-2 border-slate-800" />
          {/* Spinning arc */}
          <div className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-accent" />
          {/* Inner glow */}
          <div className="absolute inset-2 rounded-full bg-amber-500/10" />
        </div>
        <p className="font-mono text-xs tracking-widest text-slate-500 uppercase">
          Verifying session…
        </p>
      </div>
    </div>
  );
}

export default function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <FullPageSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Outlet />;
}
