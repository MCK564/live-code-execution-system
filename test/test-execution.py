from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from exceptions.DataNotFoundException import DataNotFoundException
from services import execution as execution_service


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

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commit_count += 1

    def refresh(self, item):
        self.refresh_count += 1
        if getattr(item, "id", None) is None:
            item.id = uuid4()

    def query(self, _model):
        return DummyQuery(self.query_result)


class QueueStub:
    def __init__(self, count):
        self.count = count
        self.enqueued = []

    def enqueue(self, fn, execution_id, retry):
        self.enqueued.append((fn, execution_id, retry))


def test_run_code_session_raises_when_queue_is_busy(monkeypatch):
    queue = QueueStub(count=execution_service.TASK_QUEUE_SIZE_LIMIT)
    monkeypatch.setattr(execution_service, "execution_queue", queue)
    db = DummyDB()

    with pytest.raises(Exception, match="System is busy"):
        execution_service.run_code_session(str(uuid4()), db)

    assert db.added == []
    assert queue.enqueued == []


def test_run_code_session_creates_execution_and_enqueues(monkeypatch):
    queue = QueueStub(count=0)
    monkeypatch.setattr(execution_service, "execution_queue", queue)
    db = DummyDB()

    result = execution_service.run_code_session(str(uuid4()), db)

    assert len(db.added) == 1
    assert db.commit_count == 1
    assert db.refresh_count == 1
    assert result.execution_time_ms is None
    assert isinstance(result.queued_at, datetime)
    assert len(queue.enqueued) == 1
    enqueued_fn, enqueued_execution_id, _retry = queue.enqueued[0]
    assert enqueued_fn is execution_service.run_in_docker
    assert enqueued_execution_id == str(result.id)


def test_get_execution_result_returns_execution():
    saved_execution = SimpleNamespace(id=uuid4())
    db = DummyDB(query_result=saved_execution)

    result = execution_service.get_execution_result(str(saved_execution.id), db)

    assert result is saved_execution


def test_get_execution_result_raises_when_not_found():
    db = DummyDB(query_result=None)

    with pytest.raises(DataNotFoundException):
        execution_service.get_execution_result(str(uuid4()), db)
