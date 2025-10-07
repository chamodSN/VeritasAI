import re
import asyncio
from typing import List, Dict, Any
from common.config import Config
from common.logging import logger

SENSITIVE_TERMS = [
    r'\b(race|ethnicity|gender|sex|age|religion|nationality|disability)\b',
    r'\b(black|white|hispanic|asian|male|female|old|young|christian|muslim|jewish)\b',
    r'\b(violence|bomb|kill|attack)\b'  # Added content safety
]


class ResponsibleAIService:
    async def check_query_fairness(self, query: str) -> Dict[str, Any]:
        warnings = []
        for pattern in SENSITIVE_TERMS:
            if re.search(pattern, query, re.IGNORECASE):
                warnings.append(f"Potential issue: {pattern}")
        is_fair = len(warnings) == 0
        return {"is_fair": is_fair, "warnings": warnings}


responsible_ai = ResponsibleAIService()
