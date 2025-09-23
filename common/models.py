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
    court: Optional[str] = Field(
        None, description="Court filter (e.g., 'scotus')")


class SearchResponse(BaseModel):
    case_ids: List[str] = Field(default_factory=list)
    hit_count: int = 0
    cases: List[Dict[str, Any]] = Field(default_factory=list)


class QueryRequest(BaseModel):
    query: str


class Case(BaseModel):
    case_id: str
    case_name: str
    court: str
    decision: str
    summary: Dict[str, Any]
    citations: List[str]
    related_precedents: List[Dict[str, Any]] = Field(
        default_factory=list)  # Updated to match frontend expectation


class QueryResponse(BaseModel):
    cases: List[Case]
    case_type: str
    topic: str
    date_from: str | None
    date_to: str | None

class PrecedentRequest(BaseModel):
    case_id: str
    citations: List[str]

class PrecedentResponse(BaseModel):
    related_cases: List[Dict[str, Any]] = Field(default_factory=list)
    
class SummaryRequest(BaseModel):
    case_id: str
    case_data: Optional[Dict[str, Any]] = None


class SummaryResponse(BaseModel):
    summary: Dict[str, Any]
