import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from view.api_view import router as api_router
from view.auth_view import router as auth_router
from common.logging import logger
from common.config import Config
import os
import nltk
import multiprocessing
import time


def initialize_app():
    """Initialize the application with necessary setup"""
    # Create necessary directories
    directories = ["logs", "data/embeddings", "agents/pdf", "agents/citation"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    # Initialize NLTK data
    try:
        nltk.data.find('corpora/wordnet')
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('wordnet', quiet=True)
        nltk.download('stopwords', quiet=True)


def run_service(app_module: str, port: int, service_name: str):
    """Run a uvicorn service"""
    uvicorn.run(app_module, host="0.0.0.0", port=port, log_level="info")


def start_all_services():
    """Start all VeritasAI services"""
    # Define all services to start
    services = [
        {
            "app": "agents.citation.citation_service:app",
            "port": 8003,
            "name": "Citation Service"
        },
        {
            "app": "agents.pdf.pdf_service:app", 
            "port": 8005,
            "name": "PDF Analysis Service"
        },
        {
            "app": "run:app",  # Main API service
            "port": 8000,
            "name": "Main API Service"
        }
    ]
    
    processes = []
    
    try:
        # Start each service in a separate process
        for service in services:
            process = multiprocessing.Process(
                target=run_service,
                args=(service["app"], service["port"], service["name"])
            )
            process.start()
            processes.append(process)
            time.sleep(2)  # Give each service time to start
        
        # Wait for all processes
        for process in processes:
            process.join()
            
    except KeyboardInterrupt:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()


def main():
    """Main function to run VeritasAI"""
    # Initialize the application
    initialize_app()
    
    # Start all services
    start_all_services()


# FastAPI app configuration
app = FastAPI(
    title="VeritasAI Legal Multi-Agent System", 
    version="2.0.0",
    description="Enhanced legal research system with responsible AI framework, PDF analysis, and improved CourtListener integration"
)

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
            "message": "VeritasAI Enhanced Legal Research System",
            "version": "2.0.0",
            "features": [
                "Enhanced CourtListener API Integration",
                "Responsible AI Framework (IBM)",
                "PDF Legal Document Analysis", 
                "Improved Citation Extraction",
                "Data Encryption & Security",
                "Multi-Case Analysis"
            ],
            "docs": "/docs",
            "services": {
                "main_api": "http://localhost:8000",
                "citation_service": "http://localhost:8003", 
                "pdf_service": "http://localhost:8005"
            },
            "note": "Frontend not found. Use npm frontend or check frontend/index.html"
        }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": "VeritasAI Enhanced",
        "version": "2.0.0",
        "features": [
            "Responsible AI Framework",
            "PDF Analysis", 
            "Enhanced Citations",
            "Data Encryption"
        ]
    }


@app.get("/services/status")
async def services_status():
    """Check status of all services"""
    services = {
        "main_api": {"port": 8000, "status": "running"},
        "citation_service": {"port": 8003, "status": "checking..."},
        "pdf_service": {"port": 8005, "status": "checking..."}
    }
    
    # Check if other services are running
    for service_name, info in services.items():
        if service_name != "main_api":
            try:
                import requests
                response = requests.get(f"http://localhost:{info['port']}/health", timeout=2)
                if response.status_code == 200:
                    services[service_name]["status"] = "running"
                else:
                    services[service_name]["status"] = "error"
            except:
                services[service_name]["status"] = "not_running"
    
    return {
        "services": services,
        "overall_status": "healthy" if all(s["status"] == "running" for s in services.values()) else "degraded"
    }


# Setup logging
# logger is already imported and initialized from common.logging

if __name__ == "__main__":
    main()
