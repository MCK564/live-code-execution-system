from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from exceptions.DataNotFoundException import DataNotFoundException
from services import code_session as code_session_service


class DummyQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.result


class DummyDB:
    def __init__(self, query_result=None):
        self.query_result = query_result
        self.added = []
        self.refresh_count = 0
        self.commit_count = 0
        self.closed = False

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commit_count += 1

    def refresh(self, item):
        self.refresh_count += 1
        if getattr(item, "id", None) is None:
            item.id = uuid4()
        if getattr(item, "created_at", None) is None:
            item.created_at = datetime.now(timezone.utc)
        if getattr(item, "updated_at", None) is None:
            item.updated_at = item.created_at

    def query(self, _model):
        return DummyQuery(self.query_result)

    def close(self):
        self.closed = True


class QueueStub:
    def __init__(self):
        self.enqueued = []

    def enqueue(self, fn, session_id, retry):
        self.enqueued.append((fn, session_id, retry))


class RedisStub:
    def __init__(self, initial=None, available=True):
        self.sessions = initial or {}
        self.available = available
        self.sync_flags = set()

    def cache_is_available(self):
        return self.available

    def set_session(self, session_id, payload):
        self.sessions[session_id] = dict(payload)

    def get_session(self, session_id):
        payload = self.sessions.get(session_id)
        return dict(payload) if payload else None

    def delete_session(self, session_id):
        self.sessions.pop(session_id, None)
        self.sync_flags.discard(session_id)

    def try_mark_session_sync_enqueued(self, session_id):
        if session_id in self.sync_flags:
            return False
        self.sync_flags.add(session_id)
        return True

    def clear_session_sync_enqueued(self, session_id):
        self.sync_flags.discard(session_id)


class SessionRecord:
    def __init__(
        self,
        session_id="session-id",
        language="python",
        source_code="print('old')",
        status="ACTIVE",
        created_at=None,
        updated_at=None,
    ):
        self.id = session_id
        self.language = language
        self.source_code = source_code
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or self.created_at

    @property
    def session_id(self):
        return str(self.id)


def test_create_code_session_persists_language(monkeypatch):
    redis_stub = RedisStub()
    monkeypatch.setattr(code_session_service, "redis", redis_stub)
    db = DummyDB()
    request = SimpleNamespace(language="python")

    result = code_session_service.create_code_session(request, db)

    assert len(db.added) == 1
    assert result.language == "python"
    assert result.status == "ACTIVE"
    assert result.source_code == "print('Hello World')"
    assert db.commit_count == 1
    assert db.refresh_count == 1
    assert len(redis_stub.sessions) == 1


def test_update_code_session_frequently_writes_to_redis_and_enqueues(monkeypatch):
    redis_stub = RedisStub()
    queue_stub = QueueStub()
    existing = SessionRecord()
    db = DummyDB(query_result=existing)
    request = SimpleNamespace(language="python", source_code="print('new')")

    monkeypatch.setattr(code_session_service, "redis", redis_stub)
    monkeypatch.setattr(code_session_service, "session_sync_queue", queue_stub)

    result = code_session_service.update_code_session_frequently("session-id", request, db)

    assert result.source_code == "print('new')"
    assert db.commit_count == 0
    assert db.refresh_count == 0
    assert redis_stub.sessions["session-id"]["source_code"] == "print('new')"
    assert len(queue_stub.enqueued) == 1
    queued_fn, queued_session_id, _retry = queue_stub.enqueued[0]
    assert queued_fn is code_session_service.sync_code_session_to_db
    assert queued_session_id == "session-id"


def test_update_code_session_frequently_raises_when_not_found(monkeypatch):
    redis_stub = RedisStub()
    monkeypatch.setattr(code_session_service, "redis", redis_stub)
    db = DummyDB(query_result=None)
    request = SimpleNamespace(language="python", source_code="print('new')")

    with pytest.raises(DataNotFoundException):
        code_session_service.update_code_session_frequently("missing-session", request, db)


def test_get_session_full_state_prefers_redis_snapshot(monkeypatch):
    redis_stub = RedisStub(
        {
            "session-id": {
                "session_id": "session-id",
                "status": "ACTIVE",
                "language": "python",
                "source_code": "print('from redis')",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "sync_token": "token-1",
            }
        }
    )
    stale_db_record = SessionRecord(source_code="print('from db')")
    db = DummyDB(query_result=stale_db_record)

    monkeypatch.setattr(code_session_service, "redis", redis_stub)
    monkeypatch.setattr(code_session_service, "get_last_execution_result_by_session_id", lambda *_args, **_kwargs: None)

    result = code_session_service.get_session_full_state("session-id", db)

    assert result.source_code == "print('from redis')"
    assert result.language == "python"


def test_sync_code_session_to_db_persists_latest_snapshot(monkeypatch):
    redis_stub = RedisStub(
        {
            "session-id": {
                "session_id": "session-id",
                "status": "ACTIVE",
                "language": "python",
                "source_code": "print('latest')",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "sync_token": "token-1",
            }
        }
    )
    queue_stub = QueueStub()
    existing = SessionRecord(source_code="print('old')")
    db = DummyDB(query_result=existing)

    monkeypatch.setattr(code_session_service, "redis", redis_stub)
    monkeypatch.setattr(code_session_service, "session_sync_queue", queue_stub)
    monkeypatch.setattr(code_session_service, "SessionLocal", lambda: db)

    code_session_service.sync_code_session_to_db("session-id")

    assert existing.source_code == "print('latest')"
    assert db.commit_count == 1
    assert db.refresh_count == 1
    assert db.closed is True
