import { resolveStatusTone } from "../utils/executionStatus";

export default function StatusPill({ label, status }) {
  return (
    <div className="rounded-full px-3 py-1 text-xs font-semibold tracking-wide">
      <span className={`${resolveStatusTone(status)} rounded-full px-3 py-1`}>
        {label}: {status || "N/A"}
      </span>
    </div>
  );
}
