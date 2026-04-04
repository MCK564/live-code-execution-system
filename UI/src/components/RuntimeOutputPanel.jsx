export default function RuntimeOutputPanel({
  stdout,
  stderr,
  executionTimeMs,
}) {
  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-300">
        Runtime Output
      </h2>
      <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4">
        <p className="mb-2 text-xs uppercase tracking-[0.2em] text-emerald-300">
          stdout
        </p>
        <pre className="min-h-[120px] whitespace-pre-wrap break-words font-mono text-sm text-emerald-100">
          {stdout || "No output yet."}
        </pre>
      </div>
      <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4">
        <p className="mb-2 text-xs uppercase tracking-[0.2em] text-rose-300">
          stderr
        </p>
        <pre className="min-h-[120px] whitespace-pre-wrap break-words font-mono text-sm text-rose-100">
          {stderr || "No errors."}
        </pre>
      </div>
      <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-sm">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-300">
          Execution Time
        </p>
        <p className="mt-2 font-mono text-base text-slate-100">
          {executionTimeMs ? `${executionTimeMs} ms` : "N/A"}
        </p>
      </div>
    </div>
  );
}
