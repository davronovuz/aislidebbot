from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Annotated

from api.database import get_db
from api.deps import get_current_user, require_api_secret
from api.models.user import User, Transaction, Pricing
from api.models.subscription import UserSubscription, SubscriptionPlan
from api.schemas.user import UserInfo, SubscriptionInfo, TransactionOut

router = APIRouter(prefix="/users", tags=["users"])


async def _get_price(db: AsyncSession, service_type: str, default: float) -> float:
    r = await db.execute(
        select(Pricing.price).where(Pricing.service_type == service_type, Pricing.is_active.is_(True))
    )
    v = r.scalar_one_or_none()
    return float(v) if v is not None else default


@router.get("/me", response_model=UserInfo)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Authenticated user's info — called by frontend."""
    return await _build_user_info(user, db)


@router.get("/info", response_model=UserInfo)
async def get_user_info_by_id(
    telegram_id: Annotated[int, Query()],
    _: None = Depends(require_api_secret),
    db: AsyncSession = Depends(get_db),
):
    """Bot-internal endpoint (Bearer API_SECRET). Returns user info by telegram_id."""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    return await _build_user_info(user, db)


async def _build_user_info(user: User, db: AsyncSession) -> UserInfo:
    price_per_slide = await _get_price(db, "slide_basic", 1000.0)
    price_per_page = await _get_price(db, "page_basic", 500.0)

    sub_info = None
    sub_result = await db.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == user.id,
            UserSubscription.is_active.is_(True),
        )
    )
    sub = sub_result.scalar_one_or_none()
    if sub:
        sub_info = SubscriptionInfo(
            plan_name=sub.plan_name,
            max_presentations=sub.max_presentations,
            presentations_used=sub.presentations_used,
            max_courseworks=sub.max_courseworks,
            courseworks_used=sub.courseworks_used,
            max_slides=sub.max_slides,
            expires_at=sub.expires_at,
            is_active=sub.is_active,
        )

    return UserInfo(
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        balance=float(user.balance),
        free_presentations=user.free_presentations,
        total_spent=float(user.total_spent),
        total_deposited=float(user.total_deposited),
        member_since=user.created_at.strftime("%Y-%m-%d"),
        price_per_slide=price_per_slide,
        price_per_page=price_per_page,
        subscription=sub_info,
    )


@router.get("/transactions", response_model=list[TransactionOut])
async def get_transactions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
):
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(desc(Transaction.created_at))
        .limit(limit)
    )
    return result.scalars().all()
