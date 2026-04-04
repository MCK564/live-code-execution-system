from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from rq import Retry
from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.task_queue import session_sync_queue
from dependencies.pagination import PaginationParams
from exceptions.DataNotFoundException import DataNotFoundException
from models.code_session import CodeSession as code_session
from models.enums.status import SessionStatus
from schemas.code_session import (
    CodeSessionFullState as code_session_full_state,
    CodeSessionRequest as code_session_request,
    CodeSessionResponse,
    CodeSessionUpdateRequest as code_session_update_request,
    TEMPLATES,
)
from schemas.execution import ExecutionHistory, ExecutionResultResponse as execution_result_response
from services.execution import get_last_execution_result_by_session_id, get_list_executions_by_session_id
from utils import redis
from utils.pagination import pagainate


logger = logging.getLogger(__name__)


def create_code_session(request: code_session_request, db: Session):
    session = code_session(
        language=request.language,
        source_code=TEMPLATES[request.language],
        status=SessionStatus.ACTIVE,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    payload = _payload_from_session(session)
    redis.set_session(session.session_id, payload)

    return _response_from_payload(payload)


def update_code_session_frequently(session_id: str, request: code_session_update_request, db: Session):
    cached_payload = redis.get_session(session_id)
    session = None

    if cached_payload is None:
        session = _get_session_record(session_id, db)
        if not session:
            raise DataNotFoundException(f"Session not found with id: {session_id}")
        cached_payload = _payload_from_session(session)

    updated_payload = {
        **cached_payload,
        "language": request.language,
        "source_code": request.source_code,
        "updated_at": _utc_now().isoformat(),
        "sync_token": str(uuid4()),
    }

    if not redis.cache_is_available():
        session = session or _get_session_record(session_id, db)
        if not session:
            raise DataNotFoundException(f"Session not found with id: {session_id}")
        _persist_payload_to_db(db, session, updated_payload)
        return _response_from_payload(updated_payload)

    redis.set_session(session_id, updated_payload)

    try:
        _schedule_session_sync(session_id)
    except Exception:
        redis.clear_session_sync_enqueued(session_id)
        logger.exception("Falling back to direct DB write for session %s", session_id)
        session = session or _get_session_record(session_id, db)
        if not session:
            raise DataNotFoundException(f"Session not found with id: {session_id}")
        _persist_payload_to_db(db, session, updated_payload)

    return _response_from_payload(updated_payload)


def get_session_full_state(session_id: str, db: Session):
    payload = redis.get_session(session_id)
    if payload is None:
        session = _get_session_record(session_id, db)
        if not session:
            return None
        payload = _payload_from_session(session)
        redis.set_session(session_id, payload)

    last_execution = get_last_execution_result_by_session_id(session_id, db)
    latest_execution = execution_result_response.model_validate(last_execution) if last_execution else None

    return code_session_full_state.model_validate(
        {
            "session_id": payload["session_id"],
            "status": payload["status"],
            "language": payload["language"],
            "source_code": payload["source_code"],
            "created_at": payload["created_at"],
            "updated_at": payload["updated_at"],
            "latest_execution": latest_execution,
        }
    )


def get_execution_history(session_id: str, db: Session, pagination: PaginationParams):
    query = get_list_executions_by_session_id(session_id, db, pagination)
    items, meta = pagainate(query, pagination.page, pagination.page_size)

    return ExecutionHistory(
        session_id=session_id,
        items=[execution_result_response.model_validate(item) for item in items],
        pagination=meta,
    )


def sync_code_session_to_db(session_id: str) -> None:
    snapshot = redis.get_session(session_id)
    if snapshot is None:
        redis.clear_session_sync_enqueued(session_id)
        return

    db = SessionLocal()
    try:
        session = _get_session_record(session_id, db)
        if not session:
            redis.delete_session(session_id)
            return

        _persist_payload_to_db(db, session, snapshot)
    except Exception:
        redis.clear_session_sync_enqueued(session_id)
        raise
    finally:
        db.close()

    redis.clear_session_sync_enqueued(session_id)
    latest_snapshot = redis.get_session(session_id)
    if latest_snapshot and latest_snapshot.get("sync_token") != snapshot.get("sync_token"):
        _schedule_session_sync(session_id)


def load_latest_session_snapshot(session_id: str, db: Session | None = None) -> dict | None:
    payload = redis.get_session(session_id)
    if payload is not None:
        return payload

    owns_db = db is None
    db = db or SessionLocal()
    try:
        session = _get_session_record(session_id, db)
        if not session:
            return None

        payload = _payload_from_session(session)
        redis.set_session(session_id, payload)
        return payload
    finally:
        if owns_db:
            db.close()


def _schedule_session_sync(session_id: str) -> None:
    if not redis.cache_is_available():
        return

    if not redis.try_mark_session_sync_enqueued(session_id):
        return

    try:
        session_sync_queue.enqueue(
            sync_code_session_to_db,
            session_id,
            retry=Retry(max=3, interval=[1, 5, 10]),
        )
    except Exception:
        redis.clear_session_sync_enqueued(session_id)
        raise


def _get_session_record(session_id: str, db: Session):
    return db.query(code_session).filter(code_session.id == session_id).first()


def _payload_from_session(session: code_session) -> dict:
    created_at = session.created_at or _utc_now()
    updated_at = session.updated_at or created_at

    return {
        "session_id": session.session_id,
        "status": _status_value(session.status),
        "language": session.language,
        "source_code": session.source_code or TEMPLATES.get(session.language, ""),
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
        "sync_token": str(uuid4()),
    }


def _persist_payload_to_db(db: Session, session: code_session, payload: dict) -> None:
    session.language = payload["language"]
    session.source_code = payload["source_code"]
    session.updated_at = _parse_datetime(payload["updated_at"])

    db.commit()
    db.refresh(session)


def _response_from_payload(payload: dict) -> CodeSessionResponse:
    return CodeSessionResponse.model_validate(
        {
            "session_id": payload["session_id"],
            "status": payload["status"],
            "language": payload["language"],
            "template_code": TEMPLATES.get(payload["language"]),
            "source_code": payload["source_code"],
            "created_at": payload["created_at"],
        }
    )


def _status_value(status: SessionStatus | str | None) -> str:
    if isinstance(status, SessionStatus):
        return status.value
    if hasattr(status, "value"):
        return status.value
    return status or SessionStatus.ACTIVE.value


def _parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
