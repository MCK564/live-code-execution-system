function getScoreTone(score) {
  if (score >= 85) return "border-emerald-400/30 bg-emerald-500/15 text-emerald-200";
  if (score >= 60) return "border-amber-400/30 bg-amber-500/15 text-amber-200";
  return "border-rose-400/30 bg-rose-500/15 text-rose-200";
}

export default function AnalysisScorePill({ score, issueCount }) {
  const hasScore = typeof score === "number";

  return (
    <div
      className={`rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] ${
        hasScore
          ? getScoreTone(score)
          : "border-slate-700 bg-slate-800/60 text-slate-300"
      }`}
    >
      Score: {hasScore ? `${Math.round(score)}/100` : "N/A"}
      {typeof issueCount === "number" ? ` | ${issueCount} issue(s)` : ""}
    </div>
  );
}
