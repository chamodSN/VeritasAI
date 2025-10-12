import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from view.api_view import router as api_router
from view.auth_view import router as auth_router
from common.logging import setup_logging
from common.config import Config
import os

app = FastAPI(title="VeritasAI Legal Multi-Agent System", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=Config.SESSION_SECRET_KEY)

# Include routers
app.include_router(api_router, prefix="/api")
app.include_router(auth_router, prefix="/api")

# Serve static files (frontend)
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the HTML frontend."""
    if os.path.exists("frontend/index.html"):
        return FileResponse("frontend/index.html")
    else:
        return {
            "message": "VeritasAI API is running",
            "docs": "/docs",
            "note": "Frontend not found. Use npm frontend or check frontend/index.html"
        }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "VeritasAI"}

setup_logging()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
