from fastapi import FastAPI
from typing import Optional
from agents.summary.prompting import generate_brief
from agents.summary.models import SummarizeRequest
from agents.case_finder.models import CaseDoc

app = FastAPI()

@app.post("/summarize")
async def summarize(req: SummarizeRequest):
    # Placeholder: replace with your LLM call later
    brief = generate_brief(req.case, req.mode)
    return {"brief": brief, "entities": []}  # entities will come from Step 11

