export default function SessionMeta({
  sessionId,
  executionId,
  lastSavedAt,
  runningLabel,
}) {
  return (
    <div className="grid gap-2 rounded-2xl border border-slate-800 bg-slate-950/70 p-3 text-xs sm:grid-cols-2">
      <div>
        <span className="text-slate-400">Session ID:</span>{" "}
        <span className="font-mono text-slate-200">
          {sessionId || "Not created"}
        </span>
      </div>
      <div>
        <span className="text-slate-400">Execution ID:</span>{" "}
        <span className="font-mono text-slate-200">
          {executionId || "No run yet"}
        </span>
      </div>
      <div>
        <span className="text-slate-400">Last Saved:</span>{" "}
        <span className="font-mono text-slate-200">{lastSavedAt || "N/A"}</span>
      </div>
      <div>
        <span className="text-slate-400">Queue State:</span>{" "}
        <span className="font-mono text-slate-200">{runningLabel}</span>
      </div>
    </div>
  );
}
