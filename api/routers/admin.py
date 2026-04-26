"""Admin-only endpoints — require JWT + admin telegram_id."""
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update

from api.database import get_db
from api.deps import require_admin
from api.models.user import User, Transaction, Pricing
from api.models.task import PresentationTask
from api.models.marketplace import Template, ReadyWork
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


class PriceUpdate(BaseModel):
    service_type: str
    price: float


class BalanceAdjust(BaseModel):
    telegram_id: int
    amount: float
    description: str = "Admin adjustment"


class TransactionAction(BaseModel):
    transaction_id: int
    action: str  # approve | reject
    admin_comment: str = ""


# ─── Stats ────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def admin_stats(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total_users = (await db.execute(select(func.count(User.id)))).scalar()
    active_users = (await db.execute(select(func.count(User.id)).where(User.is_blocked.is_(False)))).scalar()
    total_revenue = (await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.transaction_type == "deposit", Transaction.status == "approved")
    )).scalar()
    pending_tasks = (await db.execute(
        select(func.count(PresentationTask.id)).where(PresentationTask.status == "pending")
    )).scalar()
    pending_transactions = (await db.execute(
        select(func.count(Transaction.id)).where(Transaction.status == "pending")
    )).scalar()

    return {
        "ok": True,
        "total_users": total_users,
        "active_users": active_users,
        "total_revenue": float(total_revenue),
        "pending_tasks": pending_tasks,
        "pending_transactions": pending_transactions,
    }


# ─── Users ────────────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    result = await db.execute(
        select(User).order_by(desc(User.created_at)).limit(limit).offset(offset)
    )
    users = result.scalars().all()
    return {"ok": True, "users": [
        {"telegram_id": u.telegram_id, "username": u.username,
         "balance": float(u.balance), "total_spent": float(u.total_spent),
         "is_blocked": u.is_blocked, "created_at": str(u.created_at)}
        for u in users
    ]}


@router.post("/users/adjust-balance")
async def adjust_balance(
    body: BalanceAdjust,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.telegram_id == body.telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    balance_before = float(user.balance)
    user.balance = float(user.balance) + body.amount
    if body.amount > 0:
        user.total_deposited = float(user.total_deposited) + body.amount
    tx = Transaction(
        user_id=user.id,
        transaction_type="deposit" if body.amount > 0 else "withdrawal",
        amount=abs(body.amount),
        balance_before=balance_before,
        balance_after=float(user.balance),
        description=f"Admin: {body.description}",
        status="approved",
        admin_id=admin.id,
    )
    db.add(tx)
    return {"ok": True, "new_balance": float(user.balance)}


@router.post("/users/block")
async def block_user(
    telegram_id: int,
    blocked: bool,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(update(User).where(User.telegram_id == telegram_id).values(is_blocked=blocked))
    return {"ok": True}


# ─── Pricing ──────────────────────────────────────────────────────────────────

@router.get("/pricing")
async def get_pricing(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Pricing).order_by(Pricing.service_type))
    rows = result.scalars().all()
    return {"ok": True, "pricing": [
        {"service_type": r.service_type, "price": float(r.price), "description": r.description}
        for r in rows
    ]}


@router.post("/pricing")
async def update_price(
    body: PriceUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Pricing).where(Pricing.service_type == body.service_type))
    p = result.scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="Service type not found")
    p.price = body.price
    return {"ok": True, "service_type": body.service_type, "price": body.price}


# ─── Transactions ─────────────────────────────────────────────────────────────

@router.get("/transactions/pending")
async def pending_transactions(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction)
        .where(Transaction.status == "pending", Transaction.transaction_type == "deposit")
        .order_by(Transaction.created_at)
        .limit(50)
    )
    txs = result.scalars().all()
    return {"ok": True, "transactions": [
        {"id": t.id, "user_id": t.user_id, "amount": float(t.amount),
         "description": t.description, "receipt_file_id": t.receipt_file_id,
         "created_at": str(t.created_at)}
        for t in txs
    ]}


@router.post("/transactions/action")
async def transaction_action(
    body: TransactionAction,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Transaction).where(Transaction.id == body.transaction_id))
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.status != "pending":
        raise HTTPException(status_code=400, detail="Transaction is not pending")

    user_result = await db.execute(select(User).where(User.id == tx.user_id))
    user = user_result.scalar_one_or_none()

    if body.action == "approve":
        tx.status = "approved"
        tx.admin_id = admin.id
        if user:
            balance_before = float(user.balance)
            user.balance = float(user.balance) + float(tx.amount)
            user.total_deposited = float(user.total_deposited) + float(tx.amount)
            tx.balance_before = balance_before
            tx.balance_after = float(user.balance)
        # Notify user
        if user:
            from api.services.notification import send_message
            import asyncio
            asyncio.create_task(send_message(
                user.telegram_id,
                f"✅ <b>To'lov tasdiqlandi!</b>\n\n"
                f"💰 Miqdor: {tx.amount:,.0f} so'm\n"
                f"💳 Balans: {float(user.balance):,.0f} so'm"
            ))
    elif body.action == "reject":
        tx.status = "rejected"
        tx.admin_id = admin.id
        if user:
            from api.services.notification import send_message
            import asyncio
            asyncio.create_task(send_message(
                user.telegram_id,
                f"❌ <b>To'lov rad etildi!</b>\n\n"
                f"💰 Miqdor: {tx.amount:,.0f} so'm\n"
                f"Izoh: {body.admin_comment or 'Noma\\'lum sabab'}"
            ))
    else:
        raise HTTPException(status_code=400, detail="action must be approve or reject")

    return {"ok": True, "transaction_id": body.transaction_id, "status": tx.status}


# ─── Marketplace management ───────────────────────────────────────────────────

@router.post("/marketplace/templates")
async def add_template(
    name: str = Form(...),
    category: str = Form("general"),
    slide_count: int = Form(10),
    price: float = Form(0.0),
    colors: str = Form("linear-gradient(135deg,#ff6b35,#f7931e)"),
    file_id: str = Form(...),
    preview_file_id: str = Form(None),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    t = Template(
        name=name, category=category, slide_count=slide_count,
        price=price, colors=colors, file_id=file_id,
        preview_file_id=preview_file_id, is_premium=price > 0,
    )
    db.add(t)
    await db.flush()
    return {"ok": True, "template_id": t.id}


@router.post("/marketplace/works")
async def add_ready_work(
    title: str = Form(...),
    subject: str = Form(""),
    work_type: str = Form("mustaqil_ish"),
    page_count: int = Form(10),
    price: float = Form(0.0),
    language: str = Form("uz"),
    description: str = Form(""),
    file_id: str = Form(...),
    preview_file_id: str = Form(None),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    w = ReadyWork(
        title=title, subject=subject, work_type=work_type,
        page_count=page_count, price=price, language=language,
        description=description, file_id=file_id,
        preview_file_id=preview_file_id,
        preview_available=preview_file_id is not None,
    )
    db.add(w)
    await db.flush()
    return {"ok": True, "work_id": w.id}


@router.delete("/marketplace/templates/{template_id}")
async def delete_template(
    template_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Template).where(Template.id == template_id).values(is_active=False)
    )
    return {"ok": True}


@router.delete("/marketplace/works/{work_id}")
async def delete_work(
    work_id: int,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(ReadyWork).where(ReadyWork.id == work_id).values(is_active=False)
    )
    return {"ok": True}
