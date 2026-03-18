from types import SimpleNamespace

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

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commit_count += 1

    def refresh(self, _item):
        self.refresh_count += 1

    def query(self, _model):
        return DummyQuery(self.query_result)


def test_create_code_session_persists_language():
    db = DummyDB()
    request = SimpleNamespace(language="python")

    result = code_session_service.create_code_session(request, db)

    assert len(db.added) == 1
    assert result.language == "python"
    assert db.commit_count == 1
    assert db.refresh_count == 1


def test_update_code_session_frequently_updates_existing_session():
    existing = SimpleNamespace(language="python", source_code="print('old')")
    db = DummyDB(query_result=existing)
    request = SimpleNamespace(language="python", source_code="print('new')")

    result = code_session_service.update_code_session_frequently("session-id", request, db)

    assert result.source_code == "print('new')"
    assert db.commit_count == 1
    assert db.refresh_count == 1


def test_update_code_session_frequently_raises_when_not_found():
    db = DummyDB(query_result=None)
    request = SimpleNamespace(language="python", source_code="print('new')")

    with pytest.raises(DataNotFoundException):
        code_session_service.update_code_session_frequently("missing-session", request, db)
