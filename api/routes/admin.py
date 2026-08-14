from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Header

from core.config import settings
from api.deps import get_current_user
from services.usage import usage_tracker

router = APIRouter()


async def require_admin(x_admin_secret: str | None = Header(default=None)):
    if not x_admin_secret or x_admin_secret != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Admin access required")
    return True


@router.get("/usage/me")
async def my_usage(days: int = 30, user: dict = Depends(get_current_user)):
    usage = await usage_tracker.get_user_usage(user["user_id"], days=days)
    return {"user_id": user["user_id"], "usage": usage}


@router.get("/usage/{user_id}")
async def usage_for_user(user_id: str, days: int = 30, _: bool = Depends(require_admin)):
    usage = await usage_tracker.get_user_usage(user_id, days=days)
    return {"user_id": user_id, "usage": usage}
