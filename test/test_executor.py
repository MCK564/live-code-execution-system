import os
from types import SimpleNamespace
from unittest.mock import MagicMock, mock_open, patch

import pytest

from core.language_config import LanguageConfig
from models.enums.status import ExecutionStatus
from schemas.execution import EXECUTION_TIME_LIMIT
from utils import executor


class DummyQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.result


class DummyDB:
    def __init__(self, query_results):
        self.query_results = list(query_results)
        self.commit_count = 0
        self.refresh_count = 0
        self.close_count = 0

    def query(self, _model):
        if not self.query_results:
            raise AssertionError("Unexpected query call")
        return DummyQuery(self.query_results.pop(0))

    def commit(self):
        self.commit_count += 1

    def refresh(self, _item):
        self.refresh_count += 1

    def close(self):
        self.close_count += 1


def make_execution(session_id="session-1"):
    return SimpleNamespace(
        id="execution-record-id",
        session_id=session_id,
        status=ExecutionStatus.QUEUED,
        stdout="",
        stderr="",
        execution_time_ms=None,
        queued_at=None,
        running_at=None,
        completed_at=None,
        failed_at=None,
        timeout_at=None,
    )


def make_session(language="python", source_code="print('Hello World')"):
    return SimpleNamespace(
        id="session-1",
        language=language,
        source_code=source_code,
    )


def patch_runtime(monkeypatch, db, redis_lock=True, runtime_image_error=None):
    redis_mock = SimpleNamespace(
        set=MagicMock(return_value=redis_lock),
        delete=MagicMock(),
    )
    cache_stub = SimpleNamespace(get_session=MagicMock(return_value=None))
    monkeypatch.setattr(executor, "SessionLocal", MagicMock(return_value=db))
    monkeypatch.setattr(executor, "redis_client", redis_mock)
    monkeypatch.setattr(executor, "session_cache", cache_stub)
    monkeypatch.setattr(
        executor,
        "_get_runtime_image_error",
        MagicMock(return_value=runtime_image_error),
    )
    return redis_mock, cache_stub


def test_run_in_docker_returns_early_when_execution_not_found(monkeypatch):
    db = DummyDB([None])
    redis_mock, _cache_stub = patch_runtime(monkeypatch, db)
    run_mock = MagicMock()
    monkeypatch.setattr(executor.subprocess, "run", run_mock)

    result = executor.run_in_docker("missing-execution")

    assert result is None
    assert redis_mock.set.call_count == 0
    assert run_mock.call_count == 0
    assert db.close_count == 1


def test_run_in_docker_raises_when_redis_lock_already_exists(monkeypatch):
    saved_execution = make_execution()
    db = DummyDB([saved_execution])
    redis_mock, _cache_stub = patch_runtime(monkeypatch, db, redis_lock=False)
    run_mock = MagicMock()
    monkeypatch.setattr(executor.subprocess, "run", run_mock)

    with pytest.raises(Exception, match="Execution already in progress"):
        executor.run_in_docker("execution-id")

    assert run_mock.call_count == 0
    assert redis_mock.set.call_count == 1


def test_run_in_docker_marks_failed_when_session_not_found(monkeypatch):
    saved_execution = make_execution()
    db = DummyDB([saved_execution, None])
    redis_mock, _cache_stub = patch_runtime(monkeypatch, db, redis_lock=True)
    run_mock = MagicMock()
    monkeypatch.setattr(executor.subprocess, "run", run_mock)

    executor.run_in_docker("execution-id")

    assert saved_execution.status == ExecutionStatus.FAILED
    assert saved_execution.stderr == "Session not found"
    assert saved_execution.failed_at is not None
    assert run_mock.call_count == 0
    assert redis_mock.delete.call_count == 1


def test_run_in_docker_marks_failed_for_unsupported_language(monkeypatch):
    saved_execution = make_execution()
    session = make_session(language="ruby", source_code="puts 'hi'")
    db = DummyDB([saved_execution, session])
    redis_mock, _cache_stub = patch_runtime(monkeypatch, db, redis_lock=True)
    run_mock = MagicMock()
    monkeypatch.setattr(executor.subprocess, "run", run_mock)
    monkeypatch.setitem(
        executor.LANGUAGE_CONFIGS,
        "ruby",
        LanguageConfig(
            image="ruby:3.3",
            source_filename=None,
            compile_command=None,
            run_command="ruby -e",
            requires_compile=False,
        ),
    )

    executor.run_in_docker("execution-id")

    assert saved_execution.status == ExecutionStatus.FAILED
    assert saved_execution.stderr == "Unsupported language: ruby"
    assert saved_execution.failed_at is not None
    assert run_mock.call_count == 0
    assert redis_mock.delete.call_count == 1


def test_run_in_docker_marks_failed_when_runtime_image_is_missing(monkeypatch):
    saved_execution = make_execution()
    session = make_session(language="python", source_code="print('Hello World')")
    db = DummyDB([saved_execution, session])
    redis_mock, _cache_stub = patch_runtime(
        monkeypatch,
        db,
        redis_lock=True,
        runtime_image_error=(
            "Runtime image python:3.11 is not available locally. "
            "Pull it first with: docker pull python:3.11"
        ),
    )
    run_mock = MagicMock()
    monkeypatch.setattr(executor.subprocess, "run", run_mock)

    executor.run_in_docker("execution-id")

    assert saved_execution.status == ExecutionStatus.FAILED
    assert saved_execution.stderr == (
        "Runtime image python:3.11 is not available locally. "
        "Pull it first with: docker pull python:3.11"
    )
    assert saved_execution.failed_at is not None
    assert run_mock.call_count == 0
    assert redis_mock.delete.call_count == 1


def test_run_in_docker_completes_python_execution_successfully(monkeypatch):
    saved_execution = make_execution()
    session = make_session(language="python", source_code="print('Hello World')")
    db = DummyDB([saved_execution, session])
    redis_mock, _cache_stub = patch_runtime(monkeypatch, db, redis_lock=True)
    run_mock = MagicMock(
        return_value=SimpleNamespace(stdout="Hello World\n", stderr="", returncode=0)
    )
    monkeypatch.setattr(executor.subprocess, "run", run_mock)
    time_mock = MagicMock(side_effect=[10.0, 10.752])
    monkeypatch.setattr(executor.time, "time", time_mock)

    executor.run_in_docker("execution-id")

    assert saved_execution.status == ExecutionStatus.COMPLETED
    assert saved_execution.stdout == "Hello World\n"
    assert saved_execution.stderr == ""
    assert saved_execution.execution_time_ms == 752
    assert saved_execution.completed_at is not None
    assert run_mock.call_args.args[0][-4:] == [
        "python:3.11",
        "python",
        "-c",
        "print('Hello World')",
    ]
    assert redis_mock.delete.call_count == 1


def test_run_in_docker_marks_timeout_for_python_execution(monkeypatch):
    saved_execution = make_execution()
    session = make_session(language="python", source_code="while True: pass")
    db = DummyDB([saved_execution, session])
    redis_mock, _cache_stub = patch_runtime(monkeypatch, db, redis_lock=True)
    run_mock = MagicMock(side_effect=executor.subprocess.TimeoutExpired(cmd="docker", timeout=EXECUTION_TIME_LIMIT))
    monkeypatch.setattr(executor.subprocess, "run", run_mock)

    executor.run_in_docker("execution-id")

    assert saved_execution.status == ExecutionStatus.TIMEOUT
    assert saved_execution.execution_time_ms == EXECUTION_TIME_LIMIT * 1000
    assert saved_execution.stderr == f"Execution timed out after {EXECUTION_TIME_LIMIT} seconds"
    assert saved_execution.timeout_at is not None
    assert redis_mock.delete.call_count == 1


def test_run_in_docker_writes_java_file_and_completes(monkeypatch):
    execution_id = "6ce41158-846a-44a9-a610-b717bd4bf242"
    safe_execution_id = execution_id.replace("-", "")
    saved_execution = make_execution()
    session = make_session(
        language="java",
        source_code='public class Main { public static void main(String[] args) { System.out.println("Hello World"); } }',
    )
    db = DummyDB([saved_execution, session])
    redis_mock, _cache_stub = patch_runtime(monkeypatch, db, redis_lock=True)
    makedirs_mock = MagicMock()
    monkeypatch.setattr(executor.os, "makedirs", makedirs_mock)
    run_mock = MagicMock(
        return_value=SimpleNamespace(stdout="Hello World\n", stderr="", returncode=0)
    )
    monkeypatch.setattr(executor.subprocess, "run", run_mock)
    time_mock = MagicMock(side_effect=[20.0, 20.300])
    monkeypatch.setattr(executor.time, "time", time_mock)

    with patch("builtins.open", mock_open()) as mocked_open:
        executor.run_in_docker(execution_id)

    expected_workspace = os.path.join("/shared_workspace", safe_execution_id)
    expected_source = os.path.join(expected_workspace, "Main.java")
    expected_shell = f"cd /workspace/{safe_execution_id} && javac Main.java && java Main"

    makedirs_mock.assert_called_once_with(expected_workspace, exist_ok=True)
    mocked_open.assert_called_once_with(expected_source, "w")
    mocked_open().write.assert_called_once_with(session.source_code)
    command = run_mock.call_args.args[0]
    assert "--cap-drop=ALL" in command
    assert command[command.index("-v") + 1] == "live-code-execution-system_shared_workspace:/workspace"
    assert command[-4:] == ["eclipse-temurin:17", "sh", "-c", expected_shell]
    assert saved_execution.status == ExecutionStatus.COMPLETED
    assert saved_execution.stdout == "Hello World\n"
    assert saved_execution.execution_time_ms == 300
    assert redis_mock.delete.call_count == 1


def test_run_in_docker_marks_failed_when_java_compile_fails(monkeypatch):
    execution_id = "6ce41158-846a-44a9-a610-b717bd4bf242"
    safe_execution_id = execution_id.replace("-", "")
    saved_execution = make_execution()
    session = make_session(language="java", source_code="public class Main {")
    db = DummyDB([saved_execution, session])
    redis_mock, _cache_stub = patch_runtime(monkeypatch, db, redis_lock=True)
    monkeypatch.setattr(executor.os, "makedirs", MagicMock())
    run_mock = MagicMock(
        return_value=SimpleNamespace(
            stdout="",
            stderr="Main.java:1: error: reached end of file while parsing",
            returncode=1,
        )
    )
    monkeypatch.setattr(executor.subprocess, "run", run_mock)
    time_mock = MagicMock(side_effect=[30.0, 30.250])
    monkeypatch.setattr(executor.time, "time", time_mock)

    with patch("builtins.open", mock_open()):
        executor.run_in_docker(execution_id)

    assert run_mock.call_args.args[0][-1] == (
        f"cd /workspace/{safe_execution_id} && javac Main.java && java Main"
    )
    assert saved_execution.status == ExecutionStatus.FAILED
    assert saved_execution.stdout == ""
    assert saved_execution.stderr == "Main.java:1: error: reached end of file while parsing"
    assert saved_execution.execution_time_ms == 250
    assert saved_execution.failed_at is not None
    assert redis_mock.delete.call_count == 1


def test_run_in_docker_uses_cached_session_snapshot_when_present(monkeypatch):
    saved_execution = make_execution()
    session = make_session(language="python", source_code="print('stale')")
    db = DummyDB([saved_execution, session])
    redis_mock, cache_stub = patch_runtime(monkeypatch, db, redis_lock=True)
    cache_stub.get_session.return_value = {
        "session_id": "session-1",
        "language": "python",
        "source_code": "print('fresh from redis')",
    }
    run_mock = MagicMock(
        return_value=SimpleNamespace(stdout="fresh from redis\n", stderr="", returncode=0)
    )
    monkeypatch.setattr(executor.subprocess, "run", run_mock)
    time_mock = MagicMock(side_effect=[40.0, 40.100])
    monkeypatch.setattr(executor.time, "time", time_mock)

    executor.run_in_docker("execution-id")

    assert run_mock.call_args.args[0][-1] == "print('fresh from redis')"
    assert saved_execution.status == ExecutionStatus.COMPLETED
    assert redis_mock.delete.call_count == 1


# python -m pytest -q -p no:cacheprovider test\test_executor.py 2>&1 | Tee-Object -FilePath test-results.txt
