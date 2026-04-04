from __future__ import annotations

from analysis import Alert, AnalysisResult, AnalyzerEngine, Severity, SUPPORTED_ANALYSIS_LANGUAGES


class CodeAlertAnalyzer:
    """
    Backward-compatible wrapper around the multi-language analyzer engine.
    Supports:
    - analyze(code)
    - analyze(language, code)
    - analyze(code, language)
    """

    def __init__(self) -> None:
        self.engine = AnalyzerEngine()

    def analyze(self, *args, **kwargs) -> AnalysisResult:
        language = kwargs.get("language", "python")

        if len(args) == 1:
            code = args[0]
        elif len(args) == 2:
            first, second = args
            if isinstance(first, str) and first.lower() in SUPPORTED_ANALYSIS_LANGUAGES:
                language = first
                code = second
            else:
                code = first
                language = second
        else:
            raise TypeError("analyze() expects either code, or language + code.")

        if not isinstance(code, str):
            raise TypeError("code must be a string")
        if not isinstance(language, str):
            raise TypeError("language must be a string")

        return self.engine.analyze(language, code)

    @staticmethod
    def supported_languages() -> tuple[str, ...]:
        return SUPPORTED_ANALYSIS_LANGUAGES


__all__ = [
    "Alert",
    "AnalysisResult",
    "CodeAlertAnalyzer",
    "Severity",
]
