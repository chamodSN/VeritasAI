import re
from typing import List, Dict, Any
from common.logging import setup_logging

logger = setup_logging()

def extract_citations_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extract legal citations from text using regex patterns.
    Returns a list of citation dictionaries with metadata.
    """
    citations = []
    
    # Common legal citation patterns
    patterns = [
        # Case citations (e.g., "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020)")
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+))\s+v\.\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)),\s+(\d+)\s+([A-Za-z\.]+)\s+(\d+)\s+\(([^)]+)\)',
        
        # Federal Reporter citations (e.g., "123 F.3d 456")
        r'(\d+)\s+([Ff]\.(?:2d|3d|Supp\.)?)\s+(\d+)',
        
        # Supreme Court citations (e.g., "123 U.S. 456")
        r'(\d+)\s+U\.S\.\s+(\d+)',
        
        # State citations (e.g., "123 Cal. 456")
        r'(\d+)\s+([A-Z][a-z]+\.)\s+(\d+)',
        
        # Statutory citations (e.g., "42 U.S.C. § 1983")
        r'(\d+)\s+U\.S\.C\.\s+§\s+(\d+)',
        
        # Law review citations (e.g., "123 Harv. L. Rev. 456")
        r'(\d+)\s+([A-Z][a-z]+\.\s+[A-Z][a-z]+\.\s+Rev\.)\s+(\d+)',
        
        # General citation pattern (volume reporter page)
        r'(\d+)\s+([A-Z][a-z]+(?:\.[A-Z][a-z]+)*)\s+(\d+)',
    ]
    
    # Pattern names for better identification
    pattern_names = [
        "case_citation",
        "federal_reporter",
        "supreme_court",
        "state_citation", 
        "statutory_citation",
        "law_review",
        "general_citation"
    ]
    
    for i, pattern in enumerate(patterns):
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            citation_text = match.group(0)
            
            # Extract context (surrounding text)
            start_pos = max(0, match.start() - 50)
            end_pos = min(len(text), match.end() + 50)
            context = text[start_pos:end_pos]
            
            citation = {
                "text": citation_text,
                "type": pattern_names[i],
                "context": context,
                "position": match.start(),
                "groups": match.groups()
            }
            
            # Avoid duplicates
            if not any(c["text"] == citation_text for c in citations):
                citations.append(citation)
    
    # Sort by position in text
    citations.sort(key=lambda x: x["position"])
    
    logger.info(f"Extracted {len(citations)} citations from text")
    return citations

def extract_citations_from_documents(documents: List[str]) -> List[Dict[str, Any]]:
    """
    Extract citations from a list of document texts.
    """
    all_citations = []
    
    for i, doc_text in enumerate(documents):
        doc_citations = extract_citations_from_text(doc_text)
        
        # Add document index to each citation
        for citation in doc_citations:
            citation["document_index"] = i
            citation["document_length"] = len(doc_text)
        
        all_citations.extend(doc_citations)
    
    # Remove duplicates based on citation text
    unique_citations = []
    seen_texts = set()
    
    for citation in all_citations:
        if citation["text"] not in seen_texts:
            unique_citations.append(citation)
            seen_texts.add(citation["text"])
    
    logger.info(f"Found {len(unique_citations)} unique citations across {len(documents)} documents")
    return unique_citations

def format_citations_for_verification(citations: List[Dict[str, Any]]) -> List[str]:
    """
    Format citations for verification by the citation agent.
    """
    formatted = []
    
    for citation in citations:
        formatted_citation = f"Citation: {citation['text']} (Type: {citation['type']})"
        if citation.get('context'):
            formatted_citation += f" | Context: {citation['context'][:100]}..."
        formatted.append(formatted_citation)
    
    return formatted