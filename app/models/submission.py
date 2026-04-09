from uuid import UUID

from core.database import Base
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from models.enums import difficulty
from enum import Enum
from models.enums import status




class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("code_sessions.id"),
        nullable=False
    ) # to get session details

    user_id = Column(Integer, nullable=False)
    question_id = Column(Integer, nullable=False) # to get testcase lists

    passed_testcases = Column(Integer, nullable=False)
    total_testcases = Column(Integer, nullable=False)
    score = Column(Integer, nullable=False)

    status = Column(
        Enum(status.SubmissionStatus),
        default=status.SubmissionStatus.WRONG
    )



    created_at = Column(DateTime, default=func.now())