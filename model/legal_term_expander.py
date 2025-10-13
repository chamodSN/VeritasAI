from langchain_openai import ChatOpenAI
from typing import List
from common.config import Config
from common.logging import setup_logging

logger = setup_logging()


class LegalTermExpander:
    """LLM-based legal term expansion for better CourtListener search"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=Config.API_KEY
        )

    def expand_legal_terms(self, keywords: List[str]) -> List[str]:
        """Expand legal terms using LLM for better search coverage"""
        try:
            if not keywords:
                return []

            # Create a prompt for legal term expansion
            prompt = f"""
            You are a legal research expert. Given these legal keywords: {', '.join(keywords)}
            
            Generate 15-20 related legal terms, synonyms, and alternative phrases that would help find relevant federal court cases. 
            Include:
            - Legal synonyms and alternative terms
            - Related legal concepts and doctrines
            - Common legal phrases and terminology
            - Statutory references where relevant
            
            Return only the terms separated by commas, no explanations.
            """

            response = self.llm.invoke(prompt)
            expanded_terms = [term.strip()
                              for term in response.content.split(',')]

            # Combine original keywords with expanded terms
            all_terms = keywords + expanded_terms

            # Remove duplicates and empty strings
            unique_terms = list(dict.fromkeys(
                [term for term in all_terms if term]))

            logger.info(
                f"Expanded {len(keywords)} keywords to {len(unique_terms)} terms")
            return unique_terms[:25]  # Limit to prevent API overload

        except Exception as e:
            logger.error(f"Error expanding legal terms: {e}")
            # Fallback to original keywords
            return keywords


# Global instance
legal_term_expander = LegalTermExpander()
