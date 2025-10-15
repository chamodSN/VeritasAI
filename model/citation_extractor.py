import re
from typing import List, Dict, Any
from common.logging import setup_logging

logger = setup_logging()

def extract_citations_from_text(text: str, metadata: Dict = None) -> List[Dict[str, Any]]:
    """
    Extract legal citations from text using regex patterns.
    Returns a list of citation dictionaries with metadata and transparency details.
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
        logger.debug(f"Applying pattern '{pattern_names[i]}': {pattern}")
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            citation_text = match.group(0)
            
            # Extract expanded context (surrounding text)
            start_pos = max(0, match.start() - 100)  # Increased context window
            end_pos = min(len(text), match.end() + 100)
            context = text[start_pos:end_pos]
            
            # Assign confidence based on pattern specificity
            confidence = 0.9 if pattern_names[i] in ["case_citation", "supreme_court", "statutory_citation"] else 0.7
            
            citation = {
                "text": citation_text,
                "type": pattern_names[i],
                "context": context,
                "position": match.start(),
                "groups": match.groups(),
                "pattern_used": pattern_names[i],  # Transparency: Log pattern used
                "confidence": confidence,  # Transparency: Confidence in match
                "extraction_notes": []  # Transparency: Notes on extraction process
            }
            
            # Avoid duplicates and prefer longer matches
            is_duplicate = False
            for j, existing_citation in enumerate(citations):
                if existing_citation["text"].lower() == citation_text.lower():
                    is_duplicate = True
                    citation["extraction_notes"].append("Duplicate detected, keeping first occurrence")
                    break
                if (citation["position"] < existing_citation["position"] + len(existing_citation["text"]) and 
                    citation["position"] + len(citation_text) > existing_citation["position"]):
                    if len(citation_text) > len(existing_citation["text"]):
                        citations[j] = citation
                        citation["extraction_notes"].append("Replaced shorter overlapping citation")
                        is_duplicate = True
                    else:
                        citation["extraction_notes"].append("Skipped due to longer overlapping citation")
                        is_duplicate = True
                    break
            
            if not is_duplicate:
                citations.append(citation)
                logger.debug(f"Extracted citation: {citation_text} (Type: {pattern_names[i]}, Position: {match.start()})")
    
    # Post-filter to skip case-name-only matches unless they have volume/page hints
    valid_citations = []
    for c in citations:
        if re.search(r'\d+\s+[A-Za-z\.]+\s+\d+', c['text']) or \
           ('v.' in c['text'] and any(g for g in c.get('groups', []) if g and re.search(r'\d+', g))):
            valid_citations.append(c)
        else:
            c["extraction_notes"].append("Filtered: Lacks volume/page or valid case format")
            logger.debug(f"Filtered citation: {c['text']} (Reason: Lacks volume/page or valid case format)")
    
    # Enrich with metadata if available
    if metadata and valid_citations:
        for citation in valid_citations:
            if 'caseName' in metadata and citation['type'] == 'case_citation':
                citation['enriched_text'] = f"{metadata['caseName']} {citation['text']} ({metadata.get('court', 'Unknown')} {metadata.get('date_filed', 'Unknown')[:4]})"
                citation['extraction_notes'].append("Enriched with caseName metadata")
            elif 'cite' in metadata:
                citation['enriched_text'] = f"{metadata.get('caseName', citation['text'])} {metadata['cite']} ({metadata.get('court', 'Unknown')} {metadata.get('date_filed', 'Unknown')[:4]})"
                citation['extraction_notes'].append("Enriched with cite metadata")
    
    # Sort by position in text
    valid_citations.sort(key=lambda x: x["position"])
    
    # Add transparency note about limitations
    for citation in valid_citations:
        citation['extraction_notes'].append("Limitations: Relies on regex patterns; may miss non-standard citations or require metadata for full accuracy")
    
    logger.info(f"Extracted {len(valid_citations)} valid citations from text")
    return valid_citations

def extract_citations_from_documents(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract citations from a list of document texts with metadata.
    """
    all_citations = []
    
    for i, doc in enumerate(documents):
        doc_text = doc.get('page_content', '')
        logger.debug(f"Processing document {i+1}: {len(doc_text)} characters")
        doc_citations = extract_citations_from_text(doc_text, metadata=doc.get('metadata', {}))
        
        # Add document index to each citation
        for citation in doc_citations:
            citation["document_index"] = i
            citation["document_length"] = len(doc_text)
            citation["extraction_notes"].append(f"Extracted from document {i+1}")
        
        all_citations.extend(doc_citations)
    
    # Remove duplicates based on citation text
    unique_citations = []
    seen_texts = set()
    
    for citation in all_citations:
        text_to_check = citation.get('enriched_text', citation['text'])
        if text_to_check not in seen_texts:
            unique_citations.append(citation)
            seen_texts.add(text_to_check)
        else:
            citation["extraction_notes"].append("Removed as duplicate citation")
            logger.debug(f"Removed duplicate citation: {text_to_check}")
    
    logger.info(f"Found {len(unique_citations)} unique citations across {len(documents)} documents")
    return unique_citations

def format_citations_for_verification(citations: List[Dict[str, Any]]) -> List[str]:
    """
    Format citations for verification by the citation agent with transparency notes.
    """
    formatted = []
    
    for citation in citations:
        text_to_use = citation.get('enriched_text', citation['text'])
        formatted_citation = f"Citation: {text_to_use} (Type: {citation['type']})"
        if citation.get('context'):
            formatted_citation += f" | Context: {citation['context'][:200]}..."  # Expanded context
        formatted_citation += f" | Extraction Notes: {'; '.join(citation['extraction_notes'])}"
        formatted_citation += " | Transparency: Extracted using regex patterns; may miss non-standard citations or rely on CourtListener metadata"
        formatted.append(formatted_citation)
    
    logger.info(f"Formatted {len(formatted)} citations for verification")
    return formatted