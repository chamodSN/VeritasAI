from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class SearchRequest(BaseModel):
    case_type: str
    topic: str
    date_from: str | None
    date_to: str | None


class PrecedentRequest(BaseModel):
    case_id: str
    citations: List[str]


class PrecedentResponse(BaseModel):
    related_cases: List[Dict[str, Any]] = Field(default_factory=list)