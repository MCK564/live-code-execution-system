
from core.database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    input = Column(String(255), nullable=False)
    expected_output = Column(String(255), nullable=False)

    question_id = Column(
        Integer,
        ForeignKey("questions.id"),
        nullable=False
    )


    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

