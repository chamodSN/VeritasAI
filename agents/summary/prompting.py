from agents.case_finder.models import CaseDoc

def generate_brief(case: CaseDoc, mode: str = "brief") -> str:
    # Example stub logic: concatenate metadata + first 300 chars
    snippet = case.full_text[:300] if case.full_text else ""
    return f"Case: {case.title}\nCourt: {case.court}\nDate: {case.date}\nSnippet: {snippet}"
