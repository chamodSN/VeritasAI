from pydantic import BaseModel
from typing import Optional


class SearchRequest(BaseModel):
    case_type: str
    topic: str
    date_from: str | None
    date_to: str | None
    
class SummaryRequest(BaseModel):
    case_id: str
    case_data: Optional[Dict[str, Any]] = None


class SummaryResponse(BaseModel):
    summary: Dict[str, Any]