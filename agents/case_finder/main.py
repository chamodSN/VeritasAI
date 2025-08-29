from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import spacy
from common.security import verify_token
from common.logging import logger

app = FastAPI(title="Query Understanding Agent")

nlp = spacy.load("en_core_web_sm")


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    case_type: str
    topic: str
    date_from: str | None
    date_to: str | None


@app.post("/parse_query", response_model=QueryResponse)
async def parse_query(request: QueryRequest, token: str = Depends(verify_token)):
    try:
        doc = nlp(request.query)
        case_type = "unknown"
        topic = "unknown"
        date_from = None
        date_to = None

        for ent in doc.ents:
            if ent.label_ == "DATE":
                if "from" in request.query.lower() or "since" in request.query.lower():
                    date_from = ent.text
                elif "to" in request.query.lower() or "until" in request.query.lower():
                    date_to = ent.text
            elif ent.label_ == "LAW" or ent.label_ == "ORG":
                topic = ent.text

        if "criminal" in request.query.lower():
            case_type = "criminal"
        elif "civil" in request.query.lower():
            case_type = "civil"

        response = QueryResponse(
            case_type=case_type, topic=topic, date_from=date_from, date_to=date_to)
        logger.info(f"Parsed query: {request.query} -> {response.dict()}")
        return response
    except Exception as e:
        logger.error(f"Error parsing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
