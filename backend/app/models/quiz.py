"""Quiz model for generated assessments."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Quiz(Base):
    """Quiz model representing AI-generated assessments."""

    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    topic: Mapped[str] = mapped_column(String(255))
    questions_json: Mapped[str] = mapped_column(Text)
    score: Mapped[float | None]
    completed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="quizzes")
