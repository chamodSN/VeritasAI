from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from core.config import settings
from core.logging import logger
from core.exceptions import VeritasAIError
from services.queue import get_redis_pool, close_redis_pool

from api.routes import auth, query, pdf, admin, dockets

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("veritasai_startup", environment=settings.Environment)
    app.state.redis = await get_redis_pool()
    yield
    await close_redis_pool(app.state.redis)
    logger.info("veritasai_shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-agent legal research system powered by CourtListener + LLMs.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)


@app.exception_handler(VeritasAIError)
async def veritasai_error_handler(request: Request, exc: VeritasAIError):
    return JSONResponse(status_code=exc.http_status, content={"detail": exc.message})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME}

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(query.router, prefix="/api", tags=["query"])
app.include_router(pdf.router, prefix="/api/pdf", tags=["pdf"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(dockets.router, prefix="/api/dockets", tags=["dockets"])
