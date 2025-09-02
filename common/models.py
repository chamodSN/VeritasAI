from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class SearchRequest(BaseModel):
    case_type: str = Field(
        "unknown", description="Detected case type (criminal/civil/…)")
    topic: str = Field("unknown", description="Detected legal topic/category")
    date_from: Optional[str] = Field(
        None, description="ISO date lower bound (YYYY-MM-DD)")
    date_to: Optional[str] = Field(
        None, description="ISO date upper bound (YYYY-MM-DD)")
    raw_query: Optional[str] = Field(
        None, description="Original user query for traceability")


class CachedSearch(BaseModel):
    key: str
    request: SearchRequest
    result_case_ids: List[str]
    cases: List[Dict[str, Any]]
