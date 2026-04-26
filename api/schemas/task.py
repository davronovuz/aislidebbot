from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any


# ─── Submit schemas ───────────────────────────────────────────────────────────

class SlideContent(BaseModel):
    title: str
    content: str
    bullet_points: list[str] = []
    image_keywords: list[str] = []
    layout: str = "standard"


class SubmitPresentation(BaseModel):
    telegram_id: int
    topic: str = Field(..., min_length=2, max_length=500)
    details: str = ""
    slide_count: int = Field(10, ge=3, le=30)
    theme_id: str = "chisel"
    language: str = "uz"
    # Pre-generated content from frontend
    pre_generated: bool = False
    title: str | None = None
    subtitle: str | None = None
    slides: list[SlideContent] = []


class SubmitDocument(BaseModel):
    telegram_id: int
    work_type: str = "mustaqil_ish"
    work_name: str = "Mustaqil ish"
    topic: str = Field(..., min_length=2, max_length=500)
    subject_name: str = ""
    page_count: int = Field(10, ge=3, le=100)
    language: str = "uz"
    language_name: str = "O'zbekcha"
    details: str = ""
    file_format: str = "docx"
    student_name: str = ""
    student_group: str = ""
    teacher_name: str = ""
    teacher_rank: str = ""
    university: str = ""
    faculty: str = ""


class SubmitReadyWorkPurchase(BaseModel):
    telegram_id: int
    work_id: int


class SubmitRequest(BaseModel):
    """Unified submit endpoint — dispatches by type"""
    type: str = "presentation"  # presentation | document | ready_work_purchase
    telegram_id: int
    # Presentation fields
    topic: str | None = None
    details: str = ""
    slide_count: int = 10
    theme_id: str = "chisel"
    language: str = "uz"
    pre_generated: bool = False
    title: str | None = None
    subtitle: str | None = None
    slides: list[Any] = []
    # Document fields
    work_type: str = "mustaqil_ish"
    work_name: str = "Mustaqil ish"
    subject_name: str = ""
    page_count: int = 10
    language_name: str = "O'zbekcha"
    file_format: str = "docx"
    student_name: str = ""
    student_group: str = ""
    teacher_name: str = ""
    teacher_rank: str = ""
    university: str = ""
    faculty: str = ""
    # Ready work purchase
    work_id: int | None = None


# ─── Response schemas ─────────────────────────────────────────────────────────

class TaskOut(BaseModel):
    task_uuid: str
    presentation_type: str
    status: str
    progress: int
    slide_count: int
    amount_charged: float
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class TaskStatusOut(BaseModel):
    ok: bool = True
    task_uuid: str
    status: str
    progress: int
    presentation_type: str | None


class SubmitResponse(BaseModel):
    ok: bool = True
    task_uuid: str
    amount_charged: float
    is_free: bool = False
