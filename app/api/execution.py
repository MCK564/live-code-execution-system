from fastapi import APIRouter, Depends
from schemas.execution import ExecutionResponse as execution_response, ExecutionResultResponse as execution_result_response
from sqlalchemy.orm import Session
from core.database import get_db
from sqlalchemy.orm import Session
from services import execution


router = APIRouter(prefix="/executions", tags=["executions"])

@router.get("/{execution_id}", response_model=execution_result_response)
async def get_execution_result(execution_id: str,  db: Session = Depends(get_db)):
    return execution.get_execution_result(execution_id, db)