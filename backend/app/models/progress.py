"""Progress model for tracking user learning analytics."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Progress(Base):
    """Progress model representing user learning analytics by topic."""

    __tablename__ = "progress_tracking"
    __table_args__ = (UniqueConstraint("user_id", "topic", name="uq_user_topic"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    topic: Mapped[str] = mapped_column(String(255), index=True)
    sessions_count: Mapped[int] = mapped_column(default=0)
    avg_score: Mapped[float] = mapped_column(default=0.0)
    weak_spots_json: Mapped[str | None] = mapped_column(Text)
    last_studied_at: Mapped[datetime | None]

    # Relationships
    user: Mapped["User"] = relationship(back_populates="progress")
