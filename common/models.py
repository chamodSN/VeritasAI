from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class QueryRequest(BaseModel):
    query: str = Field(..., description="The user's search query")
    page: Optional[int] = Field(
        default=1, description="Page number for pagination")
    per_page: Optional[int] = Field(
        default=5, description="Number of results per page")


class SearchRequest(BaseModel):
    case_type: str = Field("unknown", description="Detected case type")
    topic: str = Field("unknown", description="Detected legal topic")
    date_from: Optional[str] = Field(
        None, description="ISO date lower bound (YYYY-MM-DD)")
    date_to: Optional[str] = Field(
        None, description="ISO date upper bound (YYYY-MM-DD)")
    raw_query: Optional[str] = Field(None, description="Original user query")
    court: Optional[str] = Field(None, description="Court filter")
    page: int = Field(default=1, description="Page number for pagination")
    per_page: int = Field(default=10, description="Results per page")


class SearchResponse(BaseModel):
    case_ids: List[str] = Field(default_factory=list)
    hit_count: int = 0
    cases: List[Dict[str, Any]] = Field(default_factory=list)


class Case(BaseModel):
    case_id: str
    title: str
    court: Optional[str] = None
    decision: Optional[str] = None
    docket_id: Optional[str] = None
    date: Optional[str] = None  # Added date field
    summary: Optional[Dict[str, Any]] = None
    legal_citations: Optional[List[str]] = None
    citations_count: Optional[int] = None
    related_precedents: Optional[List[Dict[str, Any]]] = None


class QueryResponse(BaseModel):
    cases: List[Case]
    case_type: str
    topic: str
    date_from: str | None
    date_to: str | None


class PrecedentRequest(BaseModel):
    case_id: str
    citations: List[str]
    case_text: Optional[str] = None


class PrecedentResponse(BaseModel):
    related_cases: List[Dict[str, Any]] = Field(default_factory=list)


class SummaryRequest(BaseModel):
    case_id: str
    case_data: Optional[Dict[str, Any]] = None
    case_text: Optional[str] = None


class SummaryResponse(BaseModel):
    summary: Dict[str, Any]


class CitationRequest(BaseModel):
    case_id: str
    case_text: Optional[str] = None


class CitationResponse(BaseModel):
    citations: List[str]
