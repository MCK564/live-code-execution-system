from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, field_validator

from analysis.contracts import Alert, AnalysisResult, Severity


class AnalyzerAlertPayload(BaseModel):
    kind: str
    severity: Severity
    line: int
    message: str
    detail: str
    fix: str | None = None
    confidence: float = 1.0


class AnalyzerResultPayload(BaseModel):
    alerts: list[AnalyzerAlertPayload]
    score: float
    summary: str
    parse_error: str | None = None


class SupportedLanguagesResponse(BaseModel):
    languages: list[str]


class AnalyzeRequest(BaseModel):
    language: str
    source_code: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("source_code", "code"),
    )

    @field_validator("source_code")
    @classmethod
    def validate_source_code(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source_code must not be blank")
        return value


class AnalyzeResponse(BaseModel):
    language: str
    result: AnalyzerResultPayload


class AnalyzeWebSocketRequest(BaseModel):
    type: Literal["analyze.request"]
    version: int = Field(ge=0)
    language: str
    source_code: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("source_code", "code"),
    )
    request_id: str | None = None

    @field_validator("source_code")
    @classmethod
    def validate_source_code(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source_code must not be blank")
        return value


class AnalyzeWebSocketResult(BaseModel):
    type: Literal["analyze.result"] = "analyze.result"
    session_id: str
    version: int
    language: str
    request_id: str | None = None
    took_ms: float
    result: AnalyzerResultPayload


class AnalyzeWebSocketError(BaseModel):
    type: Literal["analyze.error"] = "analyze.error"
    session_id: str
    error_code: str
    message: str
    version: int | None = None
    request_id: str | None = None


class PingMessage(BaseModel):
    type: Literal["ping"]
    ts: int | float | None = None


class PongMessage(BaseModel):
    type: Literal["pong"] = "pong"
    ts: int | float | None = None


def to_alert_payload(alert: Alert) -> AnalyzerAlertPayload:
    return AnalyzerAlertPayload(
        kind=alert.kind,
        severity=alert.severity,
        line=alert.line,
        message=alert.message,
        detail=alert.detail,
        fix=alert.fix,
        confidence=alert.confidence,
    )


def to_result_payload(result: AnalysisResult) -> AnalyzerResultPayload:
    return AnalyzerResultPayload(
        alerts=[to_alert_payload(alert) for alert in result.alerts],
        score=result.score,
        summary=result.summary,
        parse_error=result.parse_error,
    )
