from core.database import Base
from sqlalchemy import Column, String, Enum, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.enums import status
import uuid

class Execution(Base):
    __tablename__ = "executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default= uuid.uuid4)
    session = relationship("CodeSession", back_populates="executions")

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("code_sessions.id"),
        nullable=False
    )
    status = Column(
        Enum(status.ExecutionStatus),
        default = status.ExecutionStatus.QUEUED
    )

    stdout = Column(String)
    stderr = Column(String)
    execution_time_ms = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    queued_at = Column(DateTime(timezone=True), server_default=func.now())
    running_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    timeout_at = Column(DateTime(timezone=True))

    @property
    def execution_id(self) -> str:
        return str(self.id)
