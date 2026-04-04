export default function EditorToolbar({
  language,
  languageOptions,
  isSaving,
  isRunning,
  onLanguageChange,
  onCreateSession,
  onResetTemplate,
  onSave,
  onRun,
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <label className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-300">
        Language
      </label>
      <select
        value={language}
        onChange={(event) => onLanguageChange(event.target.value)}
        className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none ring-amber-400 transition focus:ring-2"
      >
        {languageOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      <button
        type="button"
        onClick={onCreateSession}
        className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold transition hover:border-amber-300 hover:text-amber-200"
      >
        Create Session
      </button>

      <button
        type="button"
        onClick={onResetTemplate}
        className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold transition hover:border-slate-500"
      >
        Reset Template
      </button>

      <button
        type="button"
        onClick={onSave}
        disabled={isSaving}
        className="rounded-xl bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-900 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-70"
      >
        {isSaving ? "Saving..." : "Save"}
      </button>

      <button
        type="button"
        onClick={onRun}
        disabled={isRunning}
        className="rounded-xl bg-accent px-4 py-2 text-sm font-bold text-slate-950 transition hover:bg-amber-300 disabled:cursor-not-allowed disabled:opacity-70"
      >
        {isRunning ? "Starting..." : "Run"}
      </button>
    </div>
  );
}
