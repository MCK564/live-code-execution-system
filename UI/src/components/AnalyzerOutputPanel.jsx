import { useMemo, useState } from "react";

const SEVERITY_STYLES = {
  critical: {
    badge: "bg-rose-500/15 text-rose-200 border-rose-400/30",
    bar: "bg-rose-400",
  },
  high: {
    badge: "bg-orange-500/15 text-orange-200 border-orange-400/30",
    bar: "bg-orange-400",
  },
  medium: {
    badge: "bg-amber-500/15 text-amber-200 border-amber-400/30",
    bar: "bg-amber-400",
  },
  low: {
    badge: "bg-sky-500/15 text-sky-200 border-sky-400/30",
    bar: "bg-sky-400",
  },
};

function getSeverityStyle(severity) {
  return SEVERITY_STYLES[severity?.toLowerCase()] || {
    badge: "bg-slate-500/15 text-slate-200 border-slate-400/30",
    bar: "bg-slate-400",
  };
}

function getScoreTone(score) {
  if (score >= 85) {
    return {
      pill: "bg-emerald-500/15 text-emerald-200 border-emerald-400/30",
      bar: "bg-emerald-400",
    };
  }
  if (score >= 60) {
    return {
      pill: "bg-amber-500/15 text-amber-200 border-amber-400/30",
      bar: "bg-amber-400",
    };
  }
  return {
    pill: "bg-rose-500/15 text-rose-200 border-rose-400/30",
    bar: "bg-rose-400",
  };
}

function AnalysisScoreCard({ score = 0, summary = "No analysis summary." }) {
  const tone = getScoreTone(score);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
            Analyzer Score
          </p>
          <p className="mt-2 text-2xl font-bold text-slate-100">{score}/100</p>
        </div>
        <div
          className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${tone.pill}`}
        >
          {score >= 85 ? "Healthy" : score >= 60 ? "Needs Attention" : "Risky"}
        </div>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full transition-all ${tone.bar}`}
          style={{ width: `${Math.max(0, Math.min(100, score))}%` }}
        />
      </div>

      <p className="mt-3 text-sm text-slate-300">{summary}</p>
    </div>
  );
}

function AnalyzerAlertCard({ alert, isExpanded, onToggle }) {
  const severity = String(alert?.severity || "unknown").toLowerCase();
  const style = getSeverityStyle(severity);
  const confidencePercent = Math.round((alert?.confidence || 0) * 100);

  return (
    <button
      type="button"
      onClick={onToggle}
      className="w-full rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-left transition hover:border-slate-700"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${style.badge}`}
            >
              {severity}
            </span>
            <span className="text-xs font-mono text-slate-400">
              Line {alert.line}
            </span>
          </div>
          <p className="text-sm font-semibold text-slate-100">{alert.message}</p>
        </div>
        <span className="text-xs text-slate-500">
          {isExpanded ? "Hide" : "Expand"}
        </span>
      </div>

      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800">
        <div className={`h-full rounded-full ${style.bar}`} style={{ width: "100%" }} />
      </div>

      <div className="mt-3">
        <div className="mb-1 flex items-center justify-between text-[11px] uppercase tracking-[0.18em] text-slate-500">
          <span>Confidence</span>
          <span>{confidencePercent}%</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
          <div
            className={`h-full rounded-full ${style.bar}`}
            style={{ width: `${Math.max(0, Math.min(100, confidencePercent))}%` }}
          />
        </div>
      </div>

      {isExpanded ? (
        <div className="mt-4 space-y-3 border-t border-slate-800 pt-4">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
              Detail
            </p>
            <p className="mt-1 text-sm text-slate-300">{alert.detail}</p>
          </div>
          {alert.fix ? (
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                Suggested Fix
              </p>
              <p className="mt-1 text-sm text-slate-200">{alert.fix}</p>
            </div>
          ) : null}
        </div>
      ) : null}
    </button>
  );
}

export default function AnalyzerOutputPanel({
  analysisResult,
  analysisError,
  isAnalyzing,
}) {
  const [expandedAlerts, setExpandedAlerts] = useState(() => new Set());

  const alerts = analysisResult?.alerts || [];
  const score = analysisResult?.score ?? 100;
  const summary = analysisResult?.summary || "No issues detected.";
  const parseError = analysisResult?.parse_error || null;

  const sortedAlerts = useMemo(() => {
    return [...alerts].sort((left, right) => {
      if (left.line !== right.line) return left.line - right.line;
      return String(left.severity).localeCompare(String(right.severity));
    });
  }, [alerts]);

  const toggleAlert = (key) => {
    setExpandedAlerts((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-300">
          Analysis
        </h2>
        <span className="text-xs font-medium text-slate-400">
          {isAnalyzing ? "Analyzing..." : `${sortedAlerts.length} issue(s)`}
        </span>
      </div>

      <AnalysisScoreCard score={score} summary={summary} />

      {analysisError ? (
        <div className="rounded-2xl border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-200">
          {analysisError}
        </div>
      ) : null}

      {parseError ? (
        <div className="rounded-2xl border border-amber-400/30 bg-amber-500/10 p-4 text-sm text-amber-100">
          {parseError}
        </div>
      ) : null}

      {sortedAlerts.length === 0 && !analysisError ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-sm text-slate-300">
          {isAnalyzing
            ? "Analyzer is checking the current source."
            : "No analyzer alerts for the current source."}
        </div>
      ) : null}

      {sortedAlerts.map((alert, index) => {
        const key = `${alert.kind}-${alert.line}-${index}`;
        return (
          <AnalyzerAlertCard
            key={key}
            alert={alert}
            isExpanded={expandedAlerts.has(key)}
            onToggle={() => toggleAlert(key)}
          />
        );
      })}
    </div>
  );
}
