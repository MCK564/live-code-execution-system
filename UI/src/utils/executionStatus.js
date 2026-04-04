export const TERMINAL_STATUSES = new Set([
  "COMPLETED",
  "FAILED",
  "TIMEOUT",
  "TIMED_OUT",
]);

export function resolveStatusTone(status) {
  if (status === "COMPLETED") return "bg-emerald-500/20 text-emerald-300";
  if (status === "RUNNING") return "bg-cyan-500/20 text-cyan-300";
  if (status === "QUEUED") return "bg-amber-500/20 text-amber-300";
  if (status === "FAILED" || status === "TIMEOUT" || status === "TIMED_OUT") {
    return "bg-rose-500/20 text-rose-300";
  }
  return "bg-slate-500/20 text-slate-300";
}
