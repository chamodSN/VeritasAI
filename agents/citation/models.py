from pydantic import BaseModel
from typing import Optional

class CitationRequest(BaseModel):
    title: str
    court: str
    date: str
    reporter: Optional[str]
    volume: Optional[str]
    page: Optional[str]
    url: Optional[str]
    jurisdiction: Optional[str]
    style: str = "Bluebook"
    