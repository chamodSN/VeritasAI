from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import spacy
from spacy.matcher import PhraseMatcher
import dateparser
from common.security import verify_token
from common.logging import logger

app = FastAPI(title="Query Understanding Agent")

nlp = spacy.load("en_core_web_md")


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    case_type: str
    topic: str
    date_from: str | None
    date_to: str | None


LEGAL_TOPICS = [
    "cyber fraud",
    "data privacy",
    "theft",
    "contract dispute",
    "intellectual property",
    "bribery",
    "tax evasion"
]


matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
patterns = [nlp(text) for text in LEGAL_TOPICS]
matcher.add("LEGAL_TOPICS", patterns)


@app.post("/parse_query", response_model=QueryResponse)
async def parse_query(request: QueryRequest, token: str = Depends(verify_token)):
    try:
        doc = nlp(request.query)
        case_type = "unknown"
        topic = "unknown"
        date_from = None
        date_to = None

        query_lower = request.query.lower()

        dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
        for ent in doc.ents:
            if ent.label_ == "DATE":
                parsed_date = dateparser.parse(ent.text)
                if parsed_date:
                    dates.append(parsed_date.date())

        if len(dates) >= 1:
            date_from = str(dates[0])
        if len(dates) >= 2:
            date_to = str(dates[1])

        if "criminal" in query_lower:
            case_type = "criminal"
        elif "civil" in query_lower:
            case_type = "civil"

        matches = matcher(doc)
        if matches:
            # Take first match only
            match_id, start, end = matches[0]
            topic = doc[start:end].text

        response = QueryResponse(
            case_type=case_type, topic=topic, date_from=date_from, date_to=date_to)
        logger.info(f"Parsed query: {request.query} -> {response.dict()}")
        return response
    except Exception as e:
        logger.error(f"Error parsing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
