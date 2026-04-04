import AnalyzerOutputPanel from "./AnalyzerOutputPanel";
import RuntimeOutputPanel from "./RuntimeOutputPanel";

function TabButton({ label, isActive, badge, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition ${
        isActive
          ? "border-amber-300 bg-amber-300/10 text-amber-100"
          : "border-slate-700 bg-slate-950/60 text-slate-300 hover:border-slate-500"
      }`}
    >
      <span>{label}</span>
      {badge ? (
        <span className="rounded-full bg-rose-500 px-2 py-0.5 text-[10px] text-white">
          {badge}
        </span>
      ) : null}
    </button>
  );
}

export default function OutputTabsPanel({
  activeTab,
  onChangeTab,
  stdout,
  stderr,
  executionTimeMs,
  analysisResult,
  analysisError,
  isAnalyzing,
}) {
  const issueCount = analysisResult?.alerts?.length || 0;

  return (
    <div className="space-y-4 rounded-3xl border border-slate-800 bg-slate-900/70 p-5 shadow-glass backdrop-blur">
      <div className="flex flex-wrap items-center gap-3">
        <TabButton
          label="Runtime Output"
          isActive={activeTab === "runtime"}
          onClick={() => onChangeTab("runtime")}
        />
        <TabButton
          label="Analysis"
          isActive={activeTab === "analysis"}
          badge={issueCount > 0 ? issueCount : null}
          onClick={() => onChangeTab("analysis")}
        />
      </div>

      {activeTab === "runtime" ? (
        <RuntimeOutputPanel
          stdout={stdout}
          stderr={stderr}
          executionTimeMs={executionTimeMs}
        />
      ) : (
        <AnalyzerOutputPanel
          analysisResult={analysisResult}
          analysisError={analysisError}
          isAnalyzing={isAnalyzing}
        />
      )}
    </div>
  );
}
