from pydantic import BaseModel
from datetime import datetime


class TemplateOut(BaseModel):
    id: int
    name: str
    category: str
    price: float
    slide_count: int
    preview_url: str | None
    colors: str
    is_premium: bool

    model_config = {"from_attributes": True}


class TemplateDetail(TemplateOut):
    file_id: str
    downloads: int
    created_at: datetime


class ReadyWorkOut(BaseModel):
    id: int
    title: str
    subject: str
    work_type: str
    page_count: int
    price: float
    preview_available: bool

    model_config = {"from_attributes": True}


class ReadyWorkDetail(ReadyWorkOut):
    description: str
    language: str
    preview_file_id: str | None
    downloads: int
    created_at: datetime
