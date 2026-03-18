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


def run_code_session(session_id: str, db: Session):

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

