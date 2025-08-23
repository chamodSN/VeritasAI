""""defines a data model for a legal case document that the Case Finder agent will use to store 
and process information"""

from typing import Optional

from pydantic import BaseModel


class CaseDoc(BaseModel):
    """Data model for a legal case document."""
    id: str
    title: str
    court: str
    date: str
    citation: Optional[str] = None
    url: Optional[str] = None
    jurisdiction: Optional[str] = None
    headnotes: Optional[str] = None
    full_text: Optional[str] = None
    score: Optional[float] = None
