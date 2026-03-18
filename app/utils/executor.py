import subprocess
import time
from datetime import datetime, timezone
from core.database import SessionLocal
from models.code_session import CodeSession as code_session
from models.executions import Execution as execution
from models.enums.status import ExecutionStatus
from schemas.execution import EXECUTION_TIME_LIMIT
from core.redis_client import redis_client
import logging

LANGUAGE_COMMANDS = {
    "python": ["python", "-c"],
    "java": None,   # requires compile step — extend later
    "cpp": None,    # requires compile step — extend later
}

SUPPORTED_LANGUAGES = {"python"}


def _utc_now():
    return datetime.now(timezone.utc)


def _set_execution_status(saved_execution: execution, next_status: ExecutionStatus):
    now = _utc_now()
    saved_execution.status = next_status

    if next_status == ExecutionStatus.RUNNING:
        saved_execution.running_at = now
    elif next_status == ExecutionStatus.COMPLETED:
        saved_execution.completed_at = now
    elif next_status == ExecutionStatus.FAILED:
        saved_execution.failed_at = now
    elif next_status == ExecutionStatus.TIMEOUT:
        saved_execution.timeout_at = now


def _ensure_queued_timestamp(saved_execution: execution):
    if not saved_execution.queued_at:
        saved_execution.queued_at = _utc_now()



def execute_code_task(execution_id: str):
    logging.info(f"Executing code task for execution_id: {execution_id}")
    db = SessionLocal()
    lock_key = None
    try:
        saved_execution = db.query(execution).filter(execution.id == execution_id).first()

        if not saved_execution:
            return

        _ensure_queued_timestamp(saved_execution)
        lock_key = f"lock:session:{saved_execution.session_id}"
        lock = redis_client.set(lock_key, "1", nx=True, ex=EXECUTION_TIME_LIMIT + 10)

        if not lock:
            raise Exception("Execution already in progress")

        _set_execution_status(saved_execution, ExecutionStatus.RUNNING)
        logging.info("Execution %s status -> RUNNING", execution_id)

        db.commit()
        db.refresh(saved_execution)

        session = db.query(code_session).filter(code_session.id == saved_execution.session_id).first()
        if not session:
            _set_execution_status(saved_execution, ExecutionStatus.FAILED)
            logging.info("Execution %s status -> FAILED (session not found)", execution_id)
            saved_execution.stderr = "Session not found"
            db.commit()
            return

        if session.language not in SUPPORTED_LANGUAGES:
            _set_execution_status(saved_execution, ExecutionStatus.FAILED)
            logging.info("Execution %s status -> FAILED (unsupported language)", execution_id)
            saved_execution.stderr = f"Unsupported language: {session.language}"
            db.commit()
            return

        command = LANGUAGE_COMMANDS[session.language] + [session.source_code]
        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=EXECUTION_TIME_LIMIT
            )
            elapsed_time = time.time() - start_time
            saved_execution.stdout = result.stdout
            saved_execution.stderr = result.stderr
            saved_execution.execution_time_ms = int(elapsed_time * 1000)
            final_status = (
                ExecutionStatus.COMPLETED
                if result.returncode == 0
                else ExecutionStatus.FAILED
            )
            _set_execution_status(saved_execution, final_status)
            logging.info("Execution %s status -> %s", execution_id, final_status.value)

            db.commit()
        except subprocess.TimeoutExpired:
            _set_execution_status(saved_execution, ExecutionStatus.TIMEOUT)
            logging.info("Execution %s status -> TIMEOUT", execution_id)
            saved_execution.execution_time_ms = EXECUTION_TIME_LIMIT * 1000
            saved_execution.stderr = f"Execution timed out after {EXECUTION_TIME_LIMIT} seconds"

        except Exception as e:
            _set_execution_status(saved_execution, ExecutionStatus.FAILED)
            logging.info("Execution %s status -> FAILED", execution_id)
            saved_execution.stderr = str(e)
    finally:
        if lock_key:
            redis_client.delete(lock_key)
        db.commit()
        db.close()


def run_in_docker(execution_id: str):
    db = SessionLocal()
    lock_key = None
    try:
        saved_execution = db.query(execution).filter(execution.id == execution_id).first()

        if not saved_execution:
            return

        _ensure_queued_timestamp(saved_execution)
        lock_key = f"lock:session:{saved_execution.session_id}"
        lock = redis_client.set(lock_key, "1", nx=True, ex=EXECUTION_TIME_LIMIT + 10)

        if not lock:
            raise Exception("Execution already in progress")

        _set_execution_status(saved_execution, ExecutionStatus.RUNNING)
        logging.info("Execution %s status -> RUNNING", execution_id)

        db.commit()
        db.refresh(saved_execution)

        session = db.query(code_session).filter(code_session.id == saved_execution.session_id).first()
        if not session:
            _set_execution_status(saved_execution, ExecutionStatus.FAILED)
            logging.info("Execution %s status -> FAILED (session not found)", execution_id)
            saved_execution.stderr = "Session not found"
            db.commit()
            return

        if session.language not in SUPPORTED_LANGUAGES:
            _set_execution_status(saved_execution, ExecutionStatus.FAILED)
            logging.info("Execution %s status -> FAILED (unsupported language)", execution_id)
            saved_execution.stderr = f"Unsupported language: {session.language}"
            db.commit()
            return

        command = [
            "docker", "run", "--rm",
            "--memory=256m",
            "--cpus=0.5",
            "--read-only",
            "--pids-limit=50",
            "--cap-drop=ALL",
            "--network", "none",
            "python:3.11",
            *LANGUAGE_COMMANDS[session.language],
            session.source_code
        ]

        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=EXECUTION_TIME_LIMIT
            )
            elapsed_time = time.time() - start_time
            saved_execution.stdout = result.stdout
            saved_execution.stderr = result.stderr
            saved_execution.execution_time_ms = int(elapsed_time * 1000)
            final_status = (
                ExecutionStatus.COMPLETED
                if result.returncode == 0
                else ExecutionStatus.FAILED
            )
            _set_execution_status(saved_execution, final_status)
            logging.info("Execution %s status -> %s", execution_id, final_status.value)

            db.commit()
        except subprocess.TimeoutExpired:
            _set_execution_status(saved_execution, ExecutionStatus.TIMEOUT)
            logging.info("Execution %s status -> TIMEOUT", execution_id)
            saved_execution.execution_time_ms = EXECUTION_TIME_LIMIT * 1000
            saved_execution.stderr = f"Execution timed out after {EXECUTION_TIME_LIMIT} seconds"

        except Exception as e:
            _set_execution_status(saved_execution, ExecutionStatus.FAILED)
            logging.info("Execution %s status -> FAILED", execution_id)
            saved_execution.stderr = str(e)
    finally:
        if lock_key:
            redis_client.delete(lock_key)
        db.commit()
        db.close()



