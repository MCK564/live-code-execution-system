from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from analysis import AnalyzerEngine

from schemas.analyzer import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalyzeWebSocketError,
    AnalyzeWebSocketRequest,
    AnalyzeWebSocketResult,
    PingMessage,
    PongMessage,
    SupportedLanguagesResponse,
    to_result_payload,
)


router = APIRouter(prefix="/analyzer", tags=["analyzer"])
engine = AnalyzerEngine()


@router.get("/languages", response_model=SupportedLanguagesResponse)
async def list_supported_languages() -> SupportedLanguagesResponse:
    return SupportedLanguagesResponse(languages=list(engine.supported_languages()))


@router.post("", response_model=AnalyzeResponse)
async def analyze_code(request: AnalyzeRequest) -> AnalyzeResponse:
    try:
        result = engine.analyze(request.language, request.source_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AnalyzeResponse(
        language=request.language.strip().lower(),
        result=to_result_payload(result),
    )


@router.websocket("/ws/{session_id}")
async def analyze_code_ws(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()

    while True:
        try:
            payload = await websocket.receive_json()
        except WebSocketDisconnect:
            break

        if not isinstance(payload, dict):
            await _send_error(
                websocket,
                session_id=session_id,
                error_code="invalid_message",
                message="WebSocket payload must be a JSON object.",
            )
            continue

        message_type = payload.get("type")

        if message_type == "ping":
            await _handle_ping(websocket, payload)
            continue

        if message_type == "analyze.request":
            await _handle_analyze_request(websocket, session_id, payload)
            continue

        await _send_error(
            websocket,
            session_id=session_id,
            error_code="unknown_message_type",
            message=f"Unsupported message type: {message_type}",
            version=_coerce_optional_int(payload.get("version")),
            request_id=_coerce_optional_str(payload.get("request_id")),
        )


async def _handle_ping(websocket: WebSocket, payload: dict) -> None:
    try:
        message = PingMessage.model_validate(payload)
    except ValidationError as exc:
        await websocket.send_json(
            AnalyzeWebSocketError(
                session_id="",
                error_code="invalid_ping",
                message=str(exc),
            ).model_dump(mode="json")
        )
        return

    await websocket.send_json(PongMessage(ts=message.ts).model_dump(mode="json"))


async def _handle_analyze_request(websocket: WebSocket, session_id: str, payload: dict) -> None:
    try:
        message = AnalyzeWebSocketRequest.model_validate(payload)
    except ValidationError as exc:
        await _send_error(
            websocket,
            session_id=session_id,
            error_code="invalid_request",
            message=str(exc),
            version=_coerce_optional_int(payload.get("version")),
            request_id=_coerce_optional_str(payload.get("request_id")),
        )
        return

    started_at = time.perf_counter()
    try:
        result = engine.analyze(message.language, message.source_code)
    except ValueError as exc:
        await _send_error(
            websocket,
            session_id=session_id,
            error_code="unsupported_language",
            message=str(exc),
            version=message.version,
            request_id=message.request_id,
        )
        return

    took_ms = round((time.perf_counter() - started_at) * 1000, 3)
    response = AnalyzeWebSocketResult(
        session_id=session_id,
        version=message.version,
        language=message.language.strip().lower(),
        request_id=message.request_id,
        took_ms=took_ms,
        result=to_result_payload(result),
    )
    await websocket.send_json(response.model_dump(mode="json"))


async def _send_error(
    websocket: WebSocket,
    session_id: str,
    error_code: str,
    message: str,
    version: int | None = None,
    request_id: str | None = None,
) -> None:
    await websocket.send_json(
        AnalyzeWebSocketError(
            session_id=session_id,
            error_code=error_code,
            message=message,
            version=version,
            request_id=request_id,
        ).model_dump(mode="json")
    )


def _coerce_optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _coerce_optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None
