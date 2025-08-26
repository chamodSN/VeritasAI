# agents/citation/main.py
from fastapi import FastAPI

from .styles import format_citation
from .validators import validate_url

from .models import CitationRequest

app = FastAPI()

@app.post("/format")
async def format_endpoint(req: CitationRequest):
    formatted = format_citation(req.dict())
    return {"formatted": formatted}

@app.post("/validate")
async def validate_endpoint(req: CitationRequest):
    valid, canonical = validate_url(req.url)
    return {"valid": valid, "canonical": canonical}







