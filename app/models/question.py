
from core.database import Base
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from models.enums import difficulty
from enum import Enum
from models.tag import question_tag
from sqlalchemy.orm import relationship


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    topic_id = Column(Integer, nullable=False)

    difficulty = Column(
        Enum(difficulty.Difficulty),
        default=difficulty.SessionStatus.EASY
    )

    # ── One-to-Many: 1 Question → nhiều TestCase ──
    # lazy="select"  → query riêng khi truy cập (default, dễ N+1)
    # lazy="joined"  → JOIN ngay khi load Question
    # lazy="subquery"→ subquery riêng, tốt cho list
    # lazy="dynamic" → trả về query object (deprecated ở 2.0)
    # lazy="noload"  → không load, phải explicit

    testcases = relationship(
        "TestCase",
        back_populates="question",
        cascade="all, delete-orphan",
        lazy="dynamic")

    tags = relationship(
        "Tag",
        secondary=question_tag,
        back_populates="questions",
        lazy="select"
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


    def __repr__(self):
        return f"<Question id={self.id} title={self.title!r}>"