from fastapi import APIRouter, Depends
from services import code_session as code_session_service, execution
from schemas.code_session import CodeSessionRequest as code_session_request, CodeSessionResponse as code_session_response, CodeSessionUpdateRequest as code_session_update_request
from schemas.execution import ExecutionResponse as execution_response
from core.database import get_db
from sqlalchemy.orm import Session
from models.code_session import CodeSession

from exceptions.DataNotFoundException import DataNotFoundException

router = APIRouter(prefix="/code-sessions", tags=["code-sessions"])

@router.post("", response_model=code_session_response)
async def create_code_session(
        request: code_session_request,
        db: Session = Depends(get_db)
):
    return code_session_service.create_code_session(request, db)


@router.patch("/{session_id}",response_model=code_session_response)
async def update_code_session_frequently(
        session_id: str,
        request: code_session_update_request,
        db: Session = Depends(get_db)
):
    return code_session_service.update_code_session_frequently(session_id,request, db)


@router.post("/{session_id}/run", response_model=execution_response)
async def run_code_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(CodeSession).filter(CodeSession.id == session_id).first()
    if not session:
        raise DataNotFoundException(f"Session not found with id: {session_id}")
    return execution.run_code_session(session_id, db)

