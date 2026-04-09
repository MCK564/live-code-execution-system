
from core.database import Base
from sqlalchemy import Column, Integer, String, Text, DateTime, Table, ForeignKey
from sqlalchemy.sql import func
from enum import Enum

from sqlalchemy.orm import relationship


question_tag = Table(
    "question_tag",
    Base.metadata,
    Column("question_id", Integer, ForeignKey("questions.id"), primary_key=True),
    Column("tag_id",      Integer, ForeignKey("tags.id"),      primary_key=True),
)

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)

    questions = relationship(
        "Question",
        back_populates="tags",
        cascade="all, delete-orphan",
        secondary=question_tag,
        lazy="select"
    )

    def __repr__(self):
        return f"<Tag id={self.id} name={self.name!r}>"