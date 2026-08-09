# core/models.py

from enum import Enum

class CitationStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    NEEDS_REVIEW = "NEEDS_REVIEW"

class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class CitationAnalysis(BaseModel):
    citation: str
    status: CitationStatus
    confidence: ConfidenceLevel
    issues: Optional[str] = None
    recommendations: Optional[str] = None


class CitationVerificationResult(BaseModel):
    total: int
    valid: int
    invalid: int
    needs_review: int
    citations: List[CitationAnalysis] = Field(default_factory=list)