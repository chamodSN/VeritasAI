from fastapi import FastAPI, Depends
import re
import spacy
from common.security import verify_token
from common.logging import logger
from common.config import Config
from model.courtlistener_client import courtlistener_client
from common.models import CitationRequest, CitationResponse
from typing import List, Dict, Any
import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

app = FastAPI(title="Enhanced Citation Extraction Agent")

# Download required NLTK data
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nlp = spacy.load("en_core_web_sm")
    ruler = nlp.add_pipe("entity_ruler", before="ner")
    patterns = [
        {"label": "CASE", "pattern": [{"TEXT": {"REGEX": r"^[A-Z][a-zA-Z']+"}}, {
            "LOWER": "v."}, {"TEXT": {"REGEX": r"^[A-Z][a-zA-Z']+"}}]},
        {"label": "REPORTER", "pattern": [{"LIKE_NUM": True}, {"IS_ALPHA": True}, {"LIKE_NUM": True}, {
            "TEXT": "(", "OP": "?"}, {"LIKE_NUM": True, "OP": "?"}, {"TEXT": ")", "OP": "?"}]},
        {"label": "STATUTE", "pattern": [{"LIKE_NUM": True}, {
            "IS_ALPHA": True, "OP": "+"}, {"TEXT": "§"}, {"LIKE_NUM": True}]},
        {"label": "REGULATION", "pattern": [{"LIKE_NUM": True}, {"TEXT": "C.F.R."}]},
        {"label": "FEDERAL_RULE", "pattern": [{"TEXT": "Fed."}, {"TEXT": "R."}, {"LIKE_NUM": True}]},
        {"label": "CONSTITUTION", "pattern": [{"TEXT": "U.S."}, {"TEXT": "Const."}, {"TEXT": "amend."}, {"LIKE_NUM": True}]}
    ]
    ruler.add_patterns(patterns)
    logger.info("Spacy NLP model loaded with enhanced entity ruler")
except Exception as e:
    logger.error(f"Failed to load spacy model: {str(e)}")
    nlp = None

# Initialize stopwords
stop_words = set(stopwords.words('english'))

class CitationExtractor:
    """Enhanced citation extraction with local NLP processing"""
    
    def __init__(self):
        self.case_patterns = [
            r"\b[A-Z][a-zA-Z']+(?:\s+[A-Z][a-zA-Z']+)?\s+v\.\s+[A-Z][a-zA-Z']+(?:\s+[A-Z][a-zA-Z']+)?\b",
            r"\b[A-Z][a-zA-Z']+\s+v\.\s+[A-Z][a-zA-Z']+\b"
        ]
        
        self.reporter_patterns = [
            r"\b\d+\s+[A-Z][a-zA-Z.]+\s+\d+(?:\s+\(\d{4}\))?\b",
            r"\b\d+\s+[A-Z][a-zA-Z.]+\s+\d+(?:\s+\(\d{4}\))?\s+\(\d{4}\)\b"
        ]
        
        self.statute_patterns = [
            r"\b\d+\s+U\.S\.C\.\s+§\s+\d+(?:\.\d+)?\b",
            r"\b\d+\s+U\.S\.C\.\s+§§\s+\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?\b"
        ]
        
        self.regulation_patterns = [
            r"\b\d+\s+C\.F\.R\.\s+§\s+\d+(?:\.\d+)?\b",
            r"\b\d+\s+C\.F\.R\.\s+§§\s+\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?\b"
        ]
        
        self.federal_rule_patterns = [
            r"\bFed\.\s+R\.\s+(?:Civ\.|Crim\.|App\.)\s+P\.\s+\d+(?:\.\d+)?\b"
        ]
        
        self.constitution_patterns = [
            r"\bU\.S\.\s+Const\.\s+amend\.\s+\d+\b",
            r"\bU\.S\.\s+Const\.\s+art\.\s+\d+(?:,\s*§\s*\d+)?\b"
        ]

    def clean_text(self, text: str) -> str:
        """Clean text by removing HTML tags, extra whitespace, and unnecessary characters"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might cause issues
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\"\']', '', text)
        
        # Remove excessive punctuation
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        return text.strip()

    def extract_citations_regex(self, text: str) -> List[str]:
        """Extract citations using regex patterns"""
        citations = []
        
        # Combine all patterns
        all_patterns = (self.case_patterns + self.reporter_patterns + 
                      self.statute_patterns + self.regulation_patterns + 
                      self.federal_rule_patterns + self.constitution_patterns)
        
        for pattern in all_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            citations.extend(matches)
        
        return list(set(citations))

    def extract_citations_spacy(self, text: str) -> List[str]:
        """Extract citations using spaCy NLP"""
        if not nlp:
            return []
        
        try:
            # Limit text length for performance
            text_sample = text[:10000] if len(text) > 10000 else text
            doc = nlp(text_sample)
            
            citations = []
            for ent in doc.ents:
                if ent.label_ in ("CASE", "REPORTER", "STATUTE", "REGULATION", 
                                "FEDERAL_RULE", "CONSTITUTION"):
                    citations.append(ent.text.strip())
            
            return citations
        except Exception as e:
            logger.error(f"Error extracting citations with spacy: {str(e)}")
            return []

    def extract_citations_from_text(self, case_text: str) -> List[str]:
        """Extract citations from case text using both regex and NLP"""
        if not case_text:
            logger.warning("Empty case text provided")
            return []
        
        # Clean the text first
        cleaned_text = self.clean_text(case_text)
        
        # Extract using regex
        regex_citations = self.extract_citations_regex(cleaned_text)
        
        # Extract using spaCy
        spacy_citations = self.extract_citations_spacy(cleaned_text)
        
        # Combine and deduplicate
        all_citations = list(set(regex_citations + spacy_citations))
        
        # Filter citations by length and quality
        filtered_citations = []
        for citation in all_citations:
            citation = citation.strip()
            if 5 < len(citation) < 100:  # Reasonable length
                # Check if citation contains legal terms
                if any(term in citation.lower() for term in ['v.', 'u.s.c', 'c.f.r', 'fed.', 'const.']):
                    filtered_citations.append(citation)
        
        return filtered_citations

    def extract_citations_from_multiple_cases(self, case_texts: Dict[str, str]) -> Dict[str, List[str]]:
        """Extract citations from multiple cases"""
        case_citations = {}
        
        for case_id, text in case_texts.items():
            try:
                citations = self.extract_citations_from_text(text)
                if citations:
                    case_citations[case_id] = citations
                else:
                    logger.warning(f"No citations found for case {case_id}")
            except Exception as e:
                logger.error(f"Error extracting citations from case {case_id}: {e}")
                continue
        
        return case_citations

    def rank_citations_by_relevance(self, citations: List[str], query: str) -> List[str]:
        """Rank citations by relevance to the query using TF-IDF"""
        if not citations or not query:
            return citations
        
        try:
            # Create TF-IDF vectors
            vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
            
            # Combine query and citations
            all_texts = [query] + citations
            tfidf_matrix = vectorizer.fit_transform(all_texts)
            
            # Calculate similarity between query and each citation
            query_vector = tfidf_matrix[0:1]
            citation_vectors = tfidf_matrix[1:]
            
            similarities = cosine_similarity(query_vector, citation_vectors)[0]
            
            # Sort citations by similarity score
            scored_citations = list(zip(citations, similarities))
            scored_citations.sort(key=lambda x: x[1], reverse=True)
            
            return [citation for citation, score in scored_citations]
            
        except Exception as e:
            logger.error(f"Error ranking citations: {e}")
            return citations

# Global extractor instance
citation_extractor = CitationExtractor()

async def fetch_case_text(case_id: str) -> str:
    """Fetch case text from CourtListener API"""
    try:
        text = courtlistener_client.get_case_text(case_id)
        logger.info(f"Fetched case text for {case_id}: {len(text)} characters")
        return text
    except Exception as e:
        logger.error(f"Error fetching case text for {case_id}: {str(e)}")
        return ""

@app.post("/extract_citations", response_model=CitationResponse)
async def extract_citations(request: CitationRequest, _token: str = Depends(verify_token)):
    """Extract citations from case text or case ID"""
    logger.info(f"Received citation request for case_id {request.case_id}")
    
    try:
        if not request.case_id:
            logger.warning(f"Invalid case_id {request.case_id}")
            return CitationResponse(citations=[])

        # Get case text
        case_text = request.case_text or await fetch_case_text(request.case_id)
        if not case_text or len(case_text.strip()) < 10:
            logger.warning(f"Insufficient text for case_id {request.case_id}")
            return CitationResponse(citations=[])

        # Extract citations
        citations = citation_extractor.extract_citations_from_text(case_text)
        
        # Rank by relevance if query is provided
        if hasattr(request, 'query') and request.query:
            citations = citation_extractor.rank_citations_by_relevance(citations, request.query)
        
        # Responsible AI checks
        if citations:
            citation_lengths = [len(cit) for cit in citations]
            avg_length = sum(citation_lengths) / len(citation_lengths)
            if avg_length < 10 or avg_length > 100:
                logger.warning(f"RA Check: Abnormal citation lengths (avg: {avg_length}) for case_id {request.case_id}")
            
            # Check for potential bias in citation patterns
            case_citations = len([c for c in citations if 'v.' in c.lower()])
            if case_citations / len(citations) > 0.8:
                logger.info(f"RA Check: High proportion of case citations ({case_citations}/{len(citations)})")

        return CitationResponse(citations=citations)

    except Exception as e:
        logger.error(f"Error extracting citations for case_id {request.case_id}: {str(e)}")
        return CitationResponse(citations=[])

@app.post("/extract_citations_bulk")
async def extract_citations_bulk(case_ids: List[str], _token: str = Depends(verify_token)):
    """Extract citations from multiple cases efficiently"""
    logger.info(f"Received bulk citation request for {len(case_ids)} cases")
    
    try:
        # Get case texts
        case_texts = courtlistener_client.get_multiple_cases_text(case_ids)
        
        if not case_texts:
            logger.warning("No case texts retrieved")
            return {"case_citations": {}}
        
        # Extract citations from all cases
        case_citations = citation_extractor.extract_citations_from_multiple_cases(case_texts)
        
        return {"case_citations": case_citations}

    except Exception as e:
        logger.error(f"Error in bulk citation extraction: {str(e)}")
        return {"case_citations": {}}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Citation Extraction Agent",
        "nlp_loaded": nlp is not None,
        "patterns_loaded": len(citation_extractor.case_patterns) > 0
    }