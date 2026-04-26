from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.database import Base
from datetime import datetime


class PresentationTask(Base):
    __tablename__ = "presentation_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)

    # Task type: presentation | pitch_deck | course_work
    presentation_type: Mapped[str] = mapped_column(String(50), default="presentation")
    slide_count: Mapped[int] = mapped_column(Integer, default=10)

    # JSON payload — topic, details, slides, language, theme_id, etc.
    answers: Mapped[str | None] = mapped_column(Text)

    # Status: pending | processing | completed | failed
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)

    amount_charged: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)

    # Storage: file delivered to Telegram (file_id) and optionally R2
    result_file_id: Mapped[str | None] = mapped_column(Text)   # Telegram file_id
    result_r2_key: Mapped[str | None] = mapped_column(Text)    # R2 object key

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="tasks")


from api.models.user import User  # noqa
