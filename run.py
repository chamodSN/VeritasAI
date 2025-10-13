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
import nltk
import subprocess
import sys


def initialize_nltk():
    """Initialize NLTK data if not already downloaded"""
    try:
        nltk.data.find('corpora/wordnet')
        nltk.data.find('corpora/stopwords')
    except LookupError:
        print("Downloading NLTK data...")
        nltk.download('wordnet', quiet=True)
        nltk.download('stopwords', quiet=True)
        print("✓ NLTK data downloaded")


def check_spacy_model():
    """Check if spaCy model is available"""
    try:
        import spacy
        spacy.load("en_core_web_sm")
    except OSError:
        print("Warning: spaCy model 'en_core_web_sm' not found.")
        print("Install it with: python -m spacy download en_core_web_sm")


def create_directories():
    """Create necessary directories"""
    directories = ["logs", "data/embeddings"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def initialize_app():
    """Initialize the application with necessary setup"""
    print("Initializing VeritasAI...")

    # Create directories
    create_directories()

    # Initialize NLTK
    initialize_nltk()

    # Check spaCy model
    check_spacy_model()

    print("✓ Application initialized successfully")


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
    # Initialize the application
    initialize_app()

    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=8000)
