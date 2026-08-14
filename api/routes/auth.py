from __future__ import annotations

import secrets
from datetime import datetime

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from core.config import settings
from core.logging import logger
from core.security import create_access_token
from api.deps import get_current_user, get_user_repo
from db.user_repository import UserRepository

router = APIRouter()

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

FRONTEND_URL = settings.allowed_origins_list[0] if settings.allowed_origins_list else "http://localhost:3000"


@router.get("/google")
async def google_login(request: Request):
    request.session["oauth_state"] = secrets.token_urlsafe(16)
    redirect_uri = str(request.url_for("google_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request, repo: UserRepository = Depends(get_user_repo)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as exc:
        logger.error("google_oauth_failed", error=str(exc))
        return RedirectResponse(f"{FRONTEND_URL}/?error=oauth_failed")

    userinfo = token.get("userinfo") or {}
    email = userinfo.get("email")
    if not email:
        return RedirectResponse(f"{FRONTEND_URL}/?error=no_email")

    user_id = userinfo.get("sub") or email
    user_data = {
        "user_id": user_id,
        "email": email,
        "name": userinfo.get("name", email.split("@")[0]),
        "picture": userinfo.get("picture"),
        "last_login": datetime.utcnow(),
    }
    await repo.upsert_user(user_data)

    access_token = create_access_token(user_id=user_id, email=email)
    return RedirectResponse(f"{FRONTEND_URL}/auth/callback?token={access_token}")


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    user.pop("_id", None)
    return user


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"status": "logged_out"}
