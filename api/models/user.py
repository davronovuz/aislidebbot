from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey,
    Integer, Numeric, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    free_presentations: Mapped[int] = mapped_column(Integer, default=1)
    total_spent: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    total_deposited: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    last_active: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user", lazy="select")
    tasks: Mapped[list["PresentationTask"]] = relationship(back_populates="user", lazy="select")
    subscription: Mapped["UserSubscription | None"] = relationship(back_populates="user", lazy="select")


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255))
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    transaction_type: Mapped[str] = mapped_column(String(50))  # deposit | withdrawal
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    balance_before: Mapped[float] = mapped_column(Numeric(12, 2))
    balance_after: Mapped[float] = mapped_column(Numeric(12, 2))
    description: Mapped[str | None] = mapped_column(Text)
    receipt_file_id: Mapped[str | None] = mapped_column(Text)  # Telegram file_id
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    admin_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="transactions")


class Pricing(Base):
    __tablename__ = "pricing"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_type: Mapped[str] = mapped_column(String(100), unique=True)
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(10), default="so'm")
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Import here to avoid circular
from api.models.task import PresentationTask  # noqa
from api.models.subscription import UserSubscription  # noqa
