from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class CitationRequest(BaseModel):
    case_id: str
    case_data: Optional[Dict[str, Any]] = None


class CitationResponse(BaseModel):
    citations: List[str]

class CitationRequest(BaseModel):
    case_id: str
    case_data: Optional[Dict[str, Any]] = None


class CitationResponse(BaseModel):
    citations: List[str]