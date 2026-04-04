from __future__ import annotations

from analysis.contracts import Alert, AnalysisResult, Severity


SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}

SEVERITY_WEIGHTS = {
    Severity.CRITICAL: -30.0,
    Severity.HIGH: -15.0,
    Severity.MEDIUM: -8.0,
    Severity.LOW: -3.0,
}


def sort_alerts(alerts: list[Alert]) -> list[Alert]:
    return sorted(alerts, key=lambda alert: (alert.line, SEVERITY_ORDER[alert.severity], alert.kind))


class GenericSeverityScorer:
    def score(self, alerts: list[Alert], parse_error: str | None = None) -> float:
        if parse_error:
            return 0.0

        score = 100.0
        for alert in alerts:
            score += SEVERITY_WEIGHTS[alert.severity]
        return max(0.0, min(100.0, score))

    def summarize(self, alerts: list[Alert], parse_error: str | None = None) -> str:
        if parse_error:
            return "Code could not be parsed. Fix syntax errors first."

        if not alerts:
            return "No issues detected."

        n_critical = sum(1 for alert in alerts if alert.severity == Severity.CRITICAL)
        n_high = sum(1 for alert in alerts if alert.severity == Severity.HIGH)
        n_medium = sum(1 for alert in alerts if alert.severity == Severity.MEDIUM)

        if n_critical:
            return f"{n_critical} critical issue(s) detected."
        if n_high:
            return f"{n_high} high-risk pattern(s) found."
        if n_medium:
            return f"{n_medium} medium-severity issue(s) to review."
        return "Minor issues detected."


def build_result(
    alerts: list[Alert],
    parse_error: str | None = None,
    scorer: GenericSeverityScorer | None = None,
) -> AnalysisResult:
    scorer = scorer or GenericSeverityScorer()
    ordered_alerts = sort_alerts(alerts)
    return AnalysisResult(
        alerts=ordered_alerts,
        score=scorer.score(ordered_alerts, parse_error=parse_error),
        summary=scorer.summarize(ordered_alerts, parse_error=parse_error),
        parse_error=parse_error,
    )
