import logging
from fastapi import HTTPException

from schemas.code_session import CodeSessionRequest as code_session_request, CodeSessionUpdateRequest as code_session_update_request
from schemas.code_session import CodeSessionResponse as code_session_response, TEMPLATES as templates
from schemas.execution import ExecutionResponse as execution_response, ExecutionResultResponse as execution_result_response
from sqlalchemy.orm import Session
from models.executions import Execution as execution
from core.task_queue import execution_queue, TASK_QUEUE_SIZE_LIMIT
from utils.executor import execute_code_task, run_in_docker
from rq import Retry
from datetime import datetime, timezone

from exceptions.DataNotFoundException import DataNotFoundException

from dependencies.pagination import PaginationParams

from core.redis_client import redis_client
from models.enums.status import ExecutionStatus

from schemas.execution import ExecutionRetryResponse

from schemas.execution import ExecutionCancelResponse


def run_code_session(session_id: str, db: Session):
    previous = db.query(execution).filter(
        execution.session_id == session_id,
        execution.status.in_([ExecutionStatus.RUNNING, ExecutionStatus.QUEUED])).first()

    if previous:
        cancel_execution(previous.id,db)

    if execution_queue.count >= TASK_QUEUE_SIZE_LIMIT:
        raise Exception("System is busy, please try again later")

    new_execution = execution(
        session_id = session_id,
        stdout = "",
        stderr = "",
        execution_time_ms = None,
        queued_at = datetime.now(timezone.utc)
    )

    db.add(new_execution)
    db.commit()
    db.refresh(new_execution)


    execution_queue.enqueue(
        run_in_docker,
        str(new_execution.id),
        retry=Retry(max=3, interval=[10,30,60])
    )

    return new_execution



def get_execution_result(execution_id: str, db: Session):
    saved_execution = (db.query(execution)
                       .filter(execution.id == execution_id)
                       .first())
    if not saved_execution:
        raise DataNotFoundException(f"Execution not found with id: {execution_id}")

    return saved_execution


def get_last_execution_result_by_session_id(session_id: str, db: Session):
    return (db.query(execution)
                       .filter(execution.session_id == session_id)
                       .order_by(execution.queued_at.desc())
                       .first())


def get_list_executions_by_session_id(session_id: str, db:Session, pagination: PaginationParams):
    return (db.query(execution)
                  .filter(execution.session_id == session_id)
                  .order_by(execution.queued_at.desc()))



def cancel_execution(execution_id: str, db: Session):
    exe = db.query(execution).filter(execution.id == execution_id).first()
    if not exe:
        raise DataNotFoundException(f"Execution not found with id: {execution_id}")

    if exe.status not in [ExecutionStatus.QUEUED, ExecutionStatus.RUNNING]:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel execution with status : {exe.status.value}"
        )

    lock_key = f"lock:session:{exe.session_id}"
    redis_client.delete(lock_key)
    logging.info("Cancel | execution_id=%s | redis lock released", execution_id)

    exe.status = ExecutionStatus.CANCELLED
    exe.failed_at = datetime.now(timezone.utc)
    exe.stderr = "Execution cancelled by user"

    db.commit()

    logging.info("Cancel | execution_id=%s | status -> CANCELLED", execution_id)
    return ExecutionCancelResponse(execution_id=execution_id)


def retry_execution(execution_id: str, db:Session) -> ExecutionRetryResponse:
    return None

