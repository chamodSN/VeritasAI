from agents.issue.issue_agent import issue_agent
from crewai import Task, Crew
from common.logging import logger
from typing import List, Dict, Any
import re
import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
    nlp = None

def extract_issues_local(text: str) -> List[str]:
    """Extract legal issues using local NLP processing"""
    if not text:
        return []
    
    issues = []
    
    # Common legal issue patterns
    issue_patterns = [
        r"(?:constitutional|constitution)\s+(?:issue|question|claim)",
        r"(?:due\s+process|equal\s+protection|first\s+amendment)",
        r"(?:contract|tort|property|criminal)\s+(?:law|liability)",
        r"(?:jurisdiction|standing|ripeness|mootness)",
        r"(?:statute\s+of\s+limitations|sovereign\s+immunity)",
        r"(?:administrative\s+law|regulatory|compliance)",
        r"(?:intellectual\s+property|copyright|patent|trademark)",
        r"(?:employment\s+law|discrimination|harassment)",
        r"(?:environmental\s+law|clean\s+air|clean\s+water)",
        r"(?:securities\s+law|fraud|insider\s+trading)",
        r"(?:antitrust|monopoly|competition)",
        r"(?:privacy\s+rights|data\s+protection)",
        r"(?:civil\s+rights|human\s+rights)",
        r"(?:immigration\s+law|deportation|asylum)",
        r"(?:family\s+law|divorce|custody|support)"
    ]
    
    # Extract using regex patterns
    for pattern in issue_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = ' '.join(match)
            issues.append(match.strip())
    
    # Extract using spaCy if available
    if nlp:
        try:
            doc = nlp(text[:5000])  # Limit for performance
            for sent in doc.sents:
                sent_text = sent.text.lower()
                # Look for legal terms in sentences
                if any(term in sent_text for term in [
                    'constitutional', 'statutory', 'regulatory', 'precedent',
                    'jurisdiction', 'standing', 'liability', 'damages',
                    'injunction', 'remedy', 'violation', 'breach'
                ]):
                    # Extract the sentence as a potential issue
                    if len(sent.text.strip()) > 20 and len(sent.text.strip()) < 200:
                        issues.append(sent.text.strip())
        except Exception as e:
            logger.error(f"Error in spaCy issue extraction: {e}")
    
    # Clean and deduplicate issues
    cleaned_issues = []
    seen = set()
    
    for issue in issues:
        issue = issue.strip()
        if issue and len(issue) > 10 and issue.lower() not in seen:
            cleaned_issues.append(issue)
            seen.add(issue.lower())
    
    # Limit to top 10 issues
    return cleaned_issues[:10]

def extract_issues(text: str) -> List[str]:
    """Extract legal issues using both CrewAI and local processing"""
    logger.info("Extracting legal issues from text")
    
    try:
        # First try CrewAI approach
        task = Task(
            description=f"Identify and list the key legal issues, doctrines, and precedents in the following text. Return a clean list of issues, one per line: {text[:2000]}",
            agent=issue_agent,
            expected_output="A clean list of legal issues, one per line, without additional commentary"
        )

        crew = Crew(
            agents=[issue_agent],
            tasks=[task],
            verbose=True
        )

        result = crew.kickoff()
        
        # Extract issues from CrewAI result
        if hasattr(result, 'raw'):
            crewai_issues = str(result.raw).split('\n')
        else:
            crewai_issues = str(result).split('\n')
        
        # Clean CrewAI results
        cleaned_crewai_issues = []
        for issue in crewai_issues:
            issue = issue.strip()
            if issue and not issue.startswith('#') and len(issue) > 10:
                cleaned_crewai_issues.append(issue)
        
        
        # Also get local NLP results
        local_issues = extract_issues_local(text)
        
        # Combine and deduplicate
        all_issues = list(set(cleaned_crewai_issues + local_issues))
        
        # Sort by relevance (longer, more specific issues first)
        all_issues.sort(key=len, reverse=True)
        
        # Return top 15 issues
        final_issues = all_issues[:15]
        
        return final_issues
        
    except Exception as e:
        logger.error(f"Error in CrewAI issue extraction: {e}")
        # Fallback to local processing only
        return extract_issues_local(text)
