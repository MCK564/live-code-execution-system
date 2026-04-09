from core.database import Base
from sqlalchemy import Column, String, Enum, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from models.enums import status
import uuid

class CodeSession(Base):
    __tablename__ = "code_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default = uuid.uuid4)

    status = Column(
        Enum(status.SessionStatus),
        default=status.SessionStatus.ACTIVE
    )

    language = Column(String(20))

    source_code = Column(String)

    executions = relationship("Execution", back_populates="session")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())



    @property
    def session_id(self) -> str:
        return str(self.id)