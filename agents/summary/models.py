from pydantic import BaseModel

class SummarizeRequest(BaseModel):
    case: CaseDoc
    mode: Optional[str] = "brief"