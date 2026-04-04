from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(slots=True)
class Alert:
    kind: str
    severity: Severity
    line: int
    message: str
    detail: str
    fix: str | None = None
    confidence: float = 1.0


@dataclass(slots=True)
class AnalysisResult:
    alerts: list[Alert] = field(default_factory=list)
    score: float = 100.0
    summary: str = ""
    parse_error: str | None = None


@dataclass(slots=True)
class AnalysisContext:
    language: str
    code: str
    py_tree: ast.AST | None = None
    ts_root: Any | None = None
    source_bytes: bytes | None = None
