from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import Annotated

from api.database import get_db
from api.deps import require_api_secret
from api.models.marketplace import Template, ReadyWork
from api.schemas.marketplace import TemplateOut, TemplateDetail, ReadyWorkOut, ReadyWorkDetail

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.get("/templates", response_model=list[TemplateOut])
async def list_templates(
    category: str = "",
    _: None = Depends(require_api_secret),
    db: AsyncSession = Depends(get_db),
):
    q = select(Template).where(Template.is_active.is_(True)).order_by(Template.created_at.desc())
    if category:
        q = q.where(Template.category == category)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/templates/{template_id}", response_model=TemplateDetail)
async def get_template(
    template_id: int,
    _: None = Depends(require_api_secret),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Template).where(Template.id == template_id, Template.is_active.is_(True))
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


@router.get("/works", response_model=list[ReadyWorkOut])
async def list_works(
    q: Annotated[str, Query()] = "",
    work_type: Annotated[str, Query()] = "",
    _: None = Depends(require_api_secret),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ReadyWork).where(ReadyWork.is_active.is_(True)).order_by(ReadyWork.created_at.desc())
    if work_type:
        stmt = stmt.where(ReadyWork.work_type == work_type)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(ReadyWork.title.ilike(like), ReadyWork.subject.ilike(like)))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/works/{work_id}", response_model=ReadyWorkDetail)
async def get_work(
    work_id: int,
    _: None = Depends(require_api_secret),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ReadyWork).where(ReadyWork.id == work_id, ReadyWork.is_active.is_(True))
    )
    w = result.scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="Ready work not found")
    return w
