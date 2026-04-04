export default function WorkspaceHeader() {
  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5 shadow-glass backdrop-blur">
      <p className="text-xs uppercase tracking-[0.28em] text-amber-300">
        Live Coding System
      </p>
      <h1 className="mt-3 text-2xl font-bold sm:text-3xl">
        API-Driven Execution Workspace
      </h1>
      <p className="mt-2 text-sm text-slate-300">
        Manage code sessions, sync source, run execution jobs, and monitor
        results from the backend queue.
      </p>
    </section>
  );
}
