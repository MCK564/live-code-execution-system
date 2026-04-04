from __future__ import annotations

from analysis.contracts import AnalysisContext, AnalysisResult
from analysis.cpp_rules import run_cpp_rules
from analysis.java_rules import run_java_rules
from analysis.python_parser import parse_python
from analysis.python_rules import run_python_rules
from analysis.scoring import GenericSeverityScorer, build_result
from analysis.tree_sitter_registry import SUPPORTED_TREE_SITTER_LANGUAGES, parse_tree_sitter
from analysis.tree_sitter_utils import first_error_line


SUPPORTED_ANALYSIS_LANGUAGES = ("python", *SUPPORTED_TREE_SITTER_LANGUAGES)


class AnalyzerEngine:
    def __init__(self) -> None:
        self.scorer = GenericSeverityScorer()

    def analyze(self, language: str, code: str) -> AnalysisResult:
        normalized_language = language.strip().lower()
        if normalized_language not in SUPPORTED_ANALYSIS_LANGUAGES:
            raise ValueError(f"Unsupported analysis language: {language}")

        if normalized_language == "python":
            return self._analyze_python(code)
        return self._analyze_tree_sitter(normalized_language, code)

    def _analyze_python(self, code: str) -> AnalysisResult:
        try:
            tree = parse_python(code)
        except SyntaxError as exc:
            parse_error = f"Syntax error at line {exc.lineno}: {exc.msg}"
            return build_result([], parse_error=parse_error, scorer=self.scorer)

        ctx = AnalysisContext(language="python", code=code, py_tree=tree)
        alerts = run_python_rules(ctx)
        return build_result(alerts, scorer=self.scorer)

    def _analyze_tree_sitter(self, language: str, code: str) -> AnalysisResult:
        source_bytes, root = parse_tree_sitter(language, code)
        if root is None:
            return build_result(
                [],
                parse_error="Tree-Sitter returned an empty tree.",
                scorer=self.scorer,
            )

        if root.has_error:
            error_line = first_error_line(root)
            parse_error = f"Syntax error at line {error_line}"
            return build_result([], parse_error=parse_error, scorer=self.scorer)

        ctx = AnalysisContext(
            language=language,
            code=code,
            ts_root=root,
            source_bytes=source_bytes,
        )

        if language == "java":
            alerts = run_java_rules(ctx)
        else:
            alerts = run_cpp_rules(ctx)

        return build_result(alerts, scorer=self.scorer)

    @staticmethod
    def supported_languages() -> tuple[str, ...]:
        return SUPPORTED_ANALYSIS_LANGUAGES
