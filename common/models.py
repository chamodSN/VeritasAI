from typing import List, Optional

from pydantic import BaseModel


class Case(BaseModel):
    case_name: str
    year: int
    court: str
    snippet: str
    full_text: Optional[str] = None


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    cases: List[Case]
