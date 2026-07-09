from __future__ import annotations

from datetime import datetime, date, timedelta

from core.logging import logger

_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o":      {"input": 2.50, "output": 10.00},
    "gpt-4":       {"input": 30.0, "output": 60.00},
}

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    
    pricing = _PRICING.get(model, _PRICING["gpt-4o-mini"]) # If the model name isn't in _PRICING, fall back to gpt-4o-mini pricing

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return round(input_cost + output_cost, 6)

class UsageTracker:

    def __init(self) -> None:
        self._db = None

    async def_get_collection(self):
        


