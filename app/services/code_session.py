from schemas.code_session import CodeSessionRequest as code_session_request, CodeSessionUpdateRequest as code_session_update_request
from schemas.code_session import CodeSessionResponse as code_session_response, TEMPLATES as templates
from sqlalchemy.orm import Session
from models.code_session import CodeSession as code_session

from exceptions.DataNotFoundException import DataNotFoundException


def create_code_session(request: code_session_request, db: Session):

    session = code_session(language = request.language)

    db.add(session)
    db.commit()
    db.refresh(session)

    return session

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

