from __future__ import annotations

import json

from core.redis_client import redis_client
from services.redis_service import consume_auth_code_atomic, set_auth_code


SESSION_SYNC_ENQUEUE_TTL_SECONDS = 60

def _session_key(session_id: str) -> str:
    return f"session:{session_id}:latest"


def _session_sync_flag_key(session_id: str) -> str:
    return f"session:{session_id}:sync-enqueued"


def cache_is_available() -> bool:
    return redis_client is not None


def set_session(session_id: str, payload: dict) -> None:
    if not cache_is_available():
        return
    redis_client.set(_session_key(session_id), json.dumps(payload))

def get_session(session_id: str) -> dict | None:
    if not cache_is_available():
        return None

    raw = redis_client.get(_session_key(session_id))
    if not raw:
        return None
    return json.loads(raw)

def delete_session(session_id: str) -> None:
    if not cache_is_available():
        return
    redis_client.delete(_session_key(session_id))
    redis_client.delete(_session_sync_flag_key(session_id))


def try_mark_session_sync_enqueued(session_id: str) -> bool:
    if not cache_is_available():
        return False

    return bool(
        redis_client.set(
            _session_sync_flag_key(session_id),
            "1",
            nx=True,
            ex=SESSION_SYNC_ENQUEUE_TTL_SECONDS,
        )
    )


def clear_session_sync_enqueued(session_id: str) -> None:
    if not cache_is_available():
        return
    redis_client.delete(_session_sync_flag_key(session_id))
