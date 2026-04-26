from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.database import Base
from datetime import datetime


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200))
    price: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    max_presentations: Mapped[int] = mapped_column(Integer, default=0)
    max_courseworks: Mapped[int] = mapped_column(Integer, default=0)
    max_slides: Mapped[int] = mapped_column(Integer, default=20)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("subscription_plans.id"))
    plan_name: Mapped[str] = mapped_column(String(100))

    max_presentations: Mapped[int] = mapped_column(Integer, default=0)
    presentations_used: Mapped[int] = mapped_column(Integer, default=0)
    max_courseworks: Mapped[int] = mapped_column(Integer, default=0)
    courseworks_used: Mapped[int] = mapped_column(Integer, default=0)
    max_slides: Mapped[int] = mapped_column(Integer, default=20)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="subscription")
    plan: Mapped["SubscriptionPlan"] = relationship()


from api.models.user import User  # noqa
