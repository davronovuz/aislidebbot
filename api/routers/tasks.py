import json
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from api.database import get_db
from api.deps import get_current_user, require_api_secret
from api.models.user import User, Transaction, Pricing
from api.models.task import PresentationTask
from api.models.subscription import UserSubscription
from api.schemas.task import SubmitRequest, SubmitResponse, TaskOut, TaskStatusOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])


async def _get_price(db: AsyncSession, service_type: str, default: float) -> float:
    from sqlalchemy import select
    r = await db.execute(
        select(Pricing.price).where(Pricing.service_type == service_type, Pricing.is_active.is_(True))
    )
    v = r.scalar_one_or_none()
    return float(v) if v is not None else default


async def _deduct_balance(db: AsyncSession, user: User, amount: float, description: str) -> bool:
    if float(user.balance) < amount:
        return False
    balance_before = float(user.balance)
    user.balance = float(user.balance) - amount
    user.total_spent = float(user.total_spent) + amount
    tx = Transaction(
        user_id=user.id,
        transaction_type="withdrawal",
        amount=amount,
        balance_before=balance_before,
        balance_after=float(user.balance),
        description=description,
        status="approved",
    )
    db.add(tx)
    await db.flush()
    return True


def _enqueue(task_uuid: str):
    """Enqueue to Dramatiq. Import here to avoid circular at module load."""
    from api.workers.tasks import process_presentation_task
    process_presentation_task.send(task_uuid)


@router.post("/submit", response_model=SubmitResponse)
async def submit_task(
    body: SubmitRequest,
    _: None = Depends(require_api_secret),
    db: AsyncSession = Depends(get_db),
):
    """
    Unified submission endpoint (called from Next.js frontend via bot API secret).
    Validates balance, creates task row, enqueues to Dramatiq.
    """
    telegram_id = body.telegram_id

    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        # Auto-create user on first submit (bot users may not have authed via JWT)
        user = User(telegram_id=telegram_id, free_presentations=1)
        db.add(user)
        await db.flush()

    task_uuid = str(uuid.uuid4())
    amount_charged = 0.0
    is_free = False

    if body.type == "ready_work_purchase":
        return await _handle_ready_work_purchase(body, user, db, task_uuid)

    if body.type == "document":
        page_count = body.page_count
        # Subscription check
        sub_result = await db.execute(
            select(UserSubscription).where(
                UserSubscription.user_id == user.id, UserSubscription.is_active.is_(True)
            )
        )
        sub = sub_result.scalar_one_or_none()
        if sub and (sub.max_courseworks >= 999 or sub.courseworks_used < sub.max_courseworks):
            sub.courseworks_used += 1
            is_free = True
        else:
            price_per_page = await _get_price(db, "page_basic", 500.0)
            total = price_per_page * page_count
            ok = await _deduct_balance(db, user, total, f"{body.work_name} ({page_count} sahifa)")
            if not ok:
                raise HTTPException(status_code=402, detail="insufficient_balance")
            amount_charged = total

        content_data = {
            "work_type": body.work_type, "work_name": body.work_name,
            "topic": body.topic, "subject_name": body.subject_name,
            "page_count": page_count, "language": body.language,
            "language_name": body.language_name, "details": body.details,
            "file_format": body.file_format, "student_name": body.student_name,
            "student_group": body.student_group, "teacher_name": body.teacher_name,
            "teacher_rank": body.teacher_rank, "university": body.university,
            "faculty": body.faculty,
        }
        task = PresentationTask(
            task_uuid=task_uuid, user_id=user.id, telegram_id=telegram_id,
            presentation_type="course_work", slide_count=page_count,
            answers=json.dumps(content_data, ensure_ascii=False),
            amount_charged=amount_charged,
        )

    else:
        # Presentation
        slide_count = body.slide_count
        if user.free_presentations > 0:
            user.free_presentations -= 1
            is_free = True
        else:
            price_per_slide = await _get_price(db, "slide_basic", 1000.0)
            total = price_per_slide * slide_count
            ok = await _deduct_balance(db, user, total, f"Prezentatsiya ({slide_count} slayd)")
            if not ok:
                raise HTTPException(status_code=402, detail="insufficient_balance")
            amount_charged = total

        content_data = {
            "topic": body.topic or "Mavzusiz", "details": body.details,
            "slide_count": slide_count, "theme_id": body.theme_id,
            "language": body.language,
        }
        if body.pre_generated and body.slides:
            content_data.update({
                "pre_generated": True, "title": body.title or body.topic,
                "subtitle": body.subtitle or "", "slides": [s if isinstance(s, dict) else s.model_dump() for s in body.slides],
            })
        task = PresentationTask(
            task_uuid=task_uuid, user_id=user.id, telegram_id=telegram_id,
            presentation_type="presentation", slide_count=slide_count,
            answers=json.dumps(content_data, ensure_ascii=False),
            amount_charged=amount_charged,
        )

    db.add(task)
    await db.commit()

    try:
        _enqueue(task_uuid)
    except Exception as e:
        logger.error(f"Dramatiq enqueue failed for {task_uuid}: {e}")
        # Task is in DB with 'pending' — recovery worker can requeue

    return SubmitResponse(task_uuid=task_uuid, amount_charged=amount_charged, is_free=is_free)


async def _handle_ready_work_purchase(body: SubmitRequest, user: User, db: AsyncSession, task_uuid: str) -> SubmitResponse:
    from api.models.marketplace import ReadyWork
    from api.services.notification import send_document

    work_result = await db.execute(
        select(ReadyWork).where(ReadyWork.id == body.work_id, ReadyWork.is_active.is_(True))
    )
    work = work_result.scalar_one_or_none()
    if not work:
        raise HTTPException(status_code=404, detail="Ready work not found")

    ok = await _deduct_balance(db, user, float(work.price), f"Tayyor ish: {work.title}")
    if not ok:
        raise HTTPException(status_code=402, detail="insufficient_balance")

    work.downloads += 1
    await db.commit()

    import asyncio
    from api.services.notification import send_document
    new_balance = float(user.balance)
    caption = (
        f"✅ <b>Tayyor ish yuborildi!</b>\n\n"
        f"📝 {work.title}\n"
        f"💰 To'landi: {work.price:,.0f} so'm\n"
        f"💳 Qoldi: {new_balance:,.0f} so'm"
    )
    asyncio.create_task(send_document(user.telegram_id, work.file_id, caption))
    return SubmitResponse(task_uuid=task_uuid, amount_charged=float(work.price))


@router.get("/status/{task_uuid}", response_model=TaskStatusOut)
async def get_task_status(
    task_uuid: str,
    _: None = Depends(require_api_secret),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PresentationTask).where(PresentationTask.task_uuid == task_uuid))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatusOut(
        task_uuid=task_uuid,
        status=task.status,
        progress=task.progress,
        presentation_type=task.presentation_type,
    )


@router.get("/history", response_model=list[TaskOut])
async def get_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 30,
):
    result = await db.execute(
        select(PresentationTask)
        .where(PresentationTask.user_id == user.id)
        .order_by(desc(PresentationTask.created_at))
        .limit(limit)
    )
    return result.scalars().all()
