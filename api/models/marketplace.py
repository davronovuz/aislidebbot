from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base
from datetime import datetime


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="general", index=True)
    slide_count: Mapped[int] = mapped_column(Integer, default=10)
    price: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)

    # Gradient CSS string or hex color pair
    colors: Mapped[str] = mapped_column(String(300), default="linear-gradient(135deg,#ff6b35,#f7931e)")

    # Telegram file_ids
    file_id: Mapped[str] = mapped_column(Text, nullable=False)   # .pptx
    preview_file_id: Mapped[str | None] = mapped_column(Text)    # preview image

    # Public URL (R2 or CDN) for frontend preview
    preview_url: Mapped[str | None] = mapped_column(Text)

    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    downloads: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReadyWork(Base):
    __tablename__ = "ready_works"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), default="")
    work_type: Mapped[str] = mapped_column(String(50), default="mustaqil_ish", index=True)
    page_count: Mapped[int] = mapped_column(Integer, default=10)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="uz")
    description: Mapped[str] = mapped_column(Text, default="")

    # Telegram file_ids
    file_id: Mapped[str] = mapped_column(Text, nullable=False)
    preview_file_id: Mapped[str | None] = mapped_column(Text)

    preview_available: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    downloads: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
