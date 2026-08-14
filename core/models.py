from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


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
