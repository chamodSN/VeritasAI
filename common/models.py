from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class CitationRequest(BaseModel):
    case_id: str
    case_text: Optional[str] = None
    query: Optional[str] = None

class CitationResponse(BaseModel):
    citations: List[str]

class QueryPayload(BaseModel):
    query: str

class AlertPayload(BaseModel):
    query: str
    name: str
    rate: str = "dly"

class CaseAnalysisPayload(BaseModel):
    case_ids: List[str]

class PDFUploadRequest(BaseModel):
    filename: str
    content: str  # Base64 encoded content

class PDFAnalysisResponse(BaseModel):
    success: bool
    case_text: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ResponsibleAICheck(BaseModel):
    check_type: str
    status: str  # "passed", "warning", "failed"
    message: str
    details: Optional[Dict[str, Any]] = None

class AnalysisResult(BaseModel):
    summary: str
    issues: List[str]
    arguments: str
    citations: List[str]
    analytics: str
    confidence: float
    case_count: int
    source: str
    responsible_ai_checks: List[ResponsibleAICheck]
    raw_citations: Optional[List[str]] = None
    error: Optional[str] = None
