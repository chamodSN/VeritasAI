import re
from typing import List, Dict, Any
from common.logging import setup_logging

logger = setup_logging()

def extract_citations_from_text(text: str, metadata: Dict = None) -> List[Dict[str, Any]]:
    """
    Extract legal citations from text using regex patterns.
    Returns a list of citation dictionaries with metadata.
    """
    citations = []
    
    # Refined legal citation patterns (excluding agencies, doctrines, and court names)
    patterns = [
        # Complete case citations (e.g., "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020)")
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+v\.\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s+(\d+)\s+([A-Za-z\.\d]+)\s+(\d+)\s+\(([^)]+)\)',
        
        # Federal Reporter citations (e.g., "123 F.3d 456")
        r'(\d+)\s+([Ff]\.(?:2d|3d|Supp\.)?)\s+(\d+)',
        
        # Supreme Court citations (e.g., "123 U.S. 456")
        r'(\d+)\s+U\.S\.\s+(\d+)',
        
        # State citations (e.g., "123 Cal. 456")
        r'(\d+)\s+([A-Z][a-z]+\.)\s+(\d+)',
        
        # Statutory citations (e.g., "42 U.S.C. § 1983")
        r'(\d+)\s+U\.S\.C\.\s+§\s+(\d+)',
        
        # Law review citations with year (e.g., "123 Harv. L. Rev. 456 (2020)")
        r'(\d+)\s+([A-Z][a-z]+\.\s+[A-Z]\.\s+Rev\.)\s+(\d+)\s+\((\d+)\)',
        
        # Law review citations without year (e.g., "123 Harv. L. Rev. 456")
        r'(\d+)\s+([A-Z][a-z]+\.\s+[A-Z]\.\s+Rev\.)\s+(\d+)',
        
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
        "law_review_with_year",
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
            
            # Avoid duplicates and prefer longer matches
            is_duplicate = False
            for i, existing_citation in enumerate(citations):
                if existing_citation["text"].lower() == citation_text.lower():
                    is_duplicate = True
                    break
                if (citation["position"] < existing_citation["position"] + len(existing_citation["text"]) and 
                    citation["position"] + len(citation_text) > existing_citation["position"]):
                    if len(citation_text) > len(existing_citation["text"]):
                        citations[i] = citation
                        is_duplicate = True
                        break
                    else:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                citations.append(citation)
    
    # Post-filter to skip case-name-only matches unless they have volume/page hints
    valid_citations = [c for c in citations if re.search(r'\d+\s+[A-Za-z\.]+\s+\d+', c['text']) or 
                      ('v.' in c['text'] and any(g for g in c.get('groups', []) if g and re.search(r'\d+', g)))]

    # Enrich with metadata if available
    if metadata and valid_citations:
        for citation in valid_citations:
            if 'caseName' in metadata and citation['type'] == 'case_citation':
                citation['enriched_text'] = f"{metadata['caseName']} {citation['text']} ({metadata.get('court', 'Unknown')} {metadata.get('date_filed', 'Unknown')[:4]})"
            elif 'cite' in metadata:
                citation['enriched_text'] = f"{metadata.get('caseName', citation['text'])} {metadata['cite']} ({metadata.get('court', 'Unknown')} {metadata.get('date_filed', 'Unknown')[:4]})"

    # Sort by position in text
    valid_citations.sort(key=lambda x: x["position"])
    
    logger.info(f"Extracted {len(valid_citations)} valid citations from text")
    return valid_citations

def extract_citations_from_documents(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract citations from a list of document texts with metadata.
    """
    all_citations = []
    
    for i, doc in enumerate(documents):
        doc_text = doc.get('page_content', '')
        doc_citations = extract_citations_from_text(doc_text, metadata=doc.get('metadata', {}))
        
        # Add document index to each citation
        for citation in doc_citations:
            citation["document_index"] = i
            citation["document_length"] = len(doc_text)
        
        all_citations.extend(doc_citations)
    
    # Remove duplicates based on citation text
    unique_citations = []
    seen_texts = set()
    
    for citation in all_citations:
        text_to_check = citation.get('enriched_text', citation['text'])
        if text_to_check not in seen_texts:
            unique_citations.append(citation)
            seen_texts.add(text_to_check)
    
    logger.info(f"Found {len(unique_citations)} unique citations across {len(documents)} documents")
    return unique_citations

def format_citations_for_verification(citations: List[Dict[str, Any]]) -> List[str]:
    """
    Format citations for verification by the citation agent.
    """
    formatted = []
    
    for citation in citations:
        text_to_use = citation.get('enriched_text', citation['text'])
        formatted_citation = f"Citation: {text_to_use} (Type: {citation['type']})"
        if citation.get('context'):
            formatted_citation += f" | Context: {citation['context'][:100]}..."
        formatted.append(formatted_citation)
    
    return formatted