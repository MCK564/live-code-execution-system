from fastapi import APIRouter, Depends
from schemas.execution import ExecutionResponse as execution_response, ExecutionResultResponse as execution_result_response
from sqlalchemy.orm import Session
from core.database import get_db
from sqlalchemy.orm import Session
from services import execution

from schemas.execution import ExecutionCancelResponse

router = APIRouter(prefix="/executions", tags=["executions"])

@router.get("/{execution_id}", response_model=execution_result_response)
async def get_execution_result(execution_id: str,  db: Session = Depends(get_db)):
    return execution.get_execution_result(execution_id, db)


@router.post("/{execution_id}/retry")
async def retrieve_execution(execution_id: str, db: Session = Depends(get_db)):
    return None


@router.post("/{execution_id}/cancel", response_model=ExecutionCancelResponse)
async def cancel_execution(execution_id: str, db: Session = Depends(get_db)):
    return execution.cancel_execution(execution_id, db)

