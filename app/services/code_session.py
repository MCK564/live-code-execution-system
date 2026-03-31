from schemas.code_session import CodeSessionRequest as code_session_request, CodeSessionUpdateRequest as code_session_update_request
from schemas.code_session import CodeSessionResponse as code_session_response, TEMPLATES as templates
from sqlalchemy.orm import Session
from models.code_session import CodeSession as code_session
from services.execution import get_last_execution_result_by_session_id, get_list_executions_by_session_id
from exceptions.DataNotFoundException import DataNotFoundException
from schemas.code_session import CodeSessionFullState as code_session_full_state
from schemas.execution import ExecutionResultResponse as execution_result_response
from dependencies.pagination import PaginationParams
from utils.pagination import pagainate
from schemas.execution import ExecutionHistory
from schemas.code_session import CodeSessionResponse, TEMPLATES


def create_code_session(request: code_session_request, db: Session):

    session = code_session(language = request.language)

    db.add(session)
    db.commit()
    db.refresh(session)

    return CodeSessionResponse.model_validate({
        "session_id": session.session_id,
        "status": session.status,
        "language": session.language,
        "template_code": TEMPLATES[session.language],
    })

def update_code_session_frequently(session_id: str, request: code_session_update_request, db: Session):

    session = db.query(code_session).filter(code_session.id == session_id).first()

    if not session:
        raise DataNotFoundException(f"Session not found with id: {session_id}")
    if session:
        session.language = request.language
        session.source_code = request.source_code

    db.commit()
    db.refresh(session)

    return session


def get_session_full_state(session_id: str, db: Session):
    session = (db.query(code_session).filter(code_session.id == session_id)
               .first())
    if not session:
        return None

    last_execution = get_last_execution_result_by_session_id(session_id, db)

    return code_session_full_state.model_validate({
        "session_id": session.session_id,
        "status": session.status,
        "language": session.language,
        "source_code": session.source_code,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "latest_execution": execution_result_response.model_validate(last_execution) if last_execution else None
    })

def get_execution_history(session_id: str, db: Session, pagination: PaginationParams ):
   query = get_list_executions_by_session_id(session_id, db,pagination)
   items, meta = pagainate(query, pagination.page, pagination.page_size)

   return ExecutionHistory(
       session_id=session_id,
       items=[execution_result_response.model_validate(i) for i in items],
       pagination=meta
   )