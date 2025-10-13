"""
CourtListener API v4 Client for Legal Case Research
Handles keyword extraction, expansion, and case data retrieval
"""

import os
import time
import requests
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from common.config import Config
from common.logging import setup_logging
import spacy
import nltk
from nltk.corpus import wordnet
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from model.legal_term_expander import legal_term_expander

logger = setup_logging()

# Download required NLTK data
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')


@dataclass
class CaseData:
    """Data structure for case information from CourtListener API"""
    case_name: str
    court: str
    date_filed: str
    date_modified: str
    absolute_url: str
    resource_uri: str
    casebody: Optional[Dict[str, Any]] = None
    docket_number: Optional[str] = None
    citation_count: Optional[int] = None
    precedential: Optional[bool] = None
    nature_of_suit: Optional[str] = None
    jurisdiction: Optional[str] = None


class CourtListenerClient:
    """Client for interacting with CourtListener API v4"""

    def __init__(self):
        self.api_key = Config.COURTLISTENER_API_KEY
        self.base_url = "https://www.courtlistener.com/api/rest/v4"
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }

        # Initialize NLP models
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning(
                "spaCy model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None

        self.stop_words = set(nltk.corpus.stopwords.words('english'))

    def extract_keywords(self, user_input: str) -> List[str]:
        """Extract relevant keywords from user input using NLP"""
        keywords = []

        if self.nlp:
            doc = self.nlp(user_input)
            # Extract named entities, nouns, and adjectives
            for token in doc:
                if (token.pos_ in ['NOUN', 'ADJ', 'PROPN'] and
                    token.text.lower() not in self.stop_words and
                        len(token.text) > 2):
                    keywords.append(token.text.lower())

            # Add named entities
            for ent in doc.ents:
                if ent.label_ in ['PERSON', 'ORG', 'GPE', 'LAW']:
                    keywords.append(ent.text.lower())
        else:
            # Fallback to simple word extraction
            words = user_input.lower().split()
            keywords = [
                word for word in words if word not in self.stop_words and len(word) > 2]

        return list(set(keywords))

    def expand_keywords(self, keywords: List[str]) -> List[str]:
        """Expand keywords using LLM-based legal term expansion"""
        try:
            expanded_keywords = legal_term_expander.expand_legal_terms(
                keywords)
            logger.info(
                f"LLM expanded {len(keywords)} keywords to {len(expanded_keywords)} terms")
            return expanded_keywords
        except Exception as e:
            logger.error(f"Error in LLM keyword expansion: {e}")
            # Fallback to basic expansion
            return self._basic_keyword_expansion(keywords)

    def _basic_keyword_expansion(self, keywords: List[str]) -> List[str]:
        """Basic fallback keyword expansion"""
        expanded = []
        for keyword in keywords:
            expanded.append(keyword)
            # Add some basic variations
            if keyword.endswith('s'):
                expanded.append(keyword[:-1])
            elif not keyword.endswith('s'):
                expanded.append(keyword + 's')
        return list(set(expanded))

    def search_cases(self, query: str, limit: int = 20) -> List[CaseData]:
        """Search for cases using CourtListener API"""
        logger.info("Searching cases with query: '%s', limit: %d", query, limit)

        url = f"{self.base_url}/search/"
        params = {
            'q': query,
            'stat_Precedential': 'on',
            'order_by': 'score desc',
            'stat_Non-Precedential': 'on',
            'format': 'json'
        }

        logger.info("API URL: %s", url)
        logger.info("API Params: %s", params)
        logger.info("API Headers: %s", self.headers)

        try:
            response = requests.get(
                url, headers=self.headers, params=params, timeout=30)
            logger.info("API Response Status: %d", response.status_code)

            if response.status_code != 200:
                logger.error("API Error: Status %d, Response: %s",
                             response.status_code, response.text)
                return []

            response.raise_for_status()

            data = response.json()
            logger.info("API Response Data Keys: %s", list(
                data.keys()) if isinstance(data, dict) else "Not a dict")

            results = data.get('results', [])
            logger.info("Found %d results in API response", len(results))

            cases = []
            for i, result in enumerate(results[:limit]):
                logger.info("Processing result %d/%d",
                            i+1, min(limit, len(results)))
                case_data = CaseData(
                    case_name=result.get('caseName', ''),
                    court=result.get('court', ''),
                    date_filed=result.get('dateFiled', ''),
                    date_modified=result.get('dateModified', ''),
                    absolute_url=result.get('absolute_url', ''),
                    resource_uri=result.get('resource_uri', ''),
                    docket_number=result.get('docketNumber', ''),
                    citation_count=result.get('citationCount', 0),
                    precedential=result.get('precedential', False),
                    nature_of_suit=result.get('natureOfSuit', ''),
                    jurisdiction=result.get('jurisdiction', '')
                )
                cases.append(case_data)
                logger.info("Created case: %s (%s)",
                            case_data.case_name, case_data.court)

            logger.info("Successfully processed %d cases", len(cases))
            return cases

        except requests.exceptions.RequestException as e:
            logger.error("Request error searching cases: %s", e)
            return []
        except Exception as e:
            logger.error("Unexpected error searching cases: %s", e)
            return []

    def get_case_details(self, resource_uri: str) -> Optional[Dict[str, Any]]:
        """Get detailed case information including casebody"""
        try:
            response = requests.get(
                resource_uri, headers=self.headers, timeout=30)
            response.raise_for_status()

            case_data = response.json()

            # Get casebody if available
            if 'casebody' in case_data:
                casebody_url = case_data['casebody']
                casebody_response = requests.get(
                    casebody_url, headers=self.headers, timeout=30)
                if casebody_response.status_code == 200:
                    case_data['casebody'] = casebody_response.json()

            return case_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting case details: {e}")
            return None

    def get_opinions(self, case_id: str) -> List[Dict[str, Any]]:
        """Get opinions for a specific case"""
        url = f"{self.base_url}/opinions/"
        params = {
            'cluster': case_id,
            'format': 'json'
        }

        try:
            response = requests.get(
                url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            return data.get('results', [])

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting opinions: {e}")
            return []

    def create_alert(self, query: str, name: str) -> Optional[str]:
        """Create an alert for new cases matching the query"""
        url = f"{self.base_url}/alerts/"
        data = {
            'name': name,
            'query': query,
            'rate': 'dly'  # daily
        }

        try:
            response = requests.post(
                url, headers=self.headers, json=data, timeout=30)
            response.raise_for_status()

            alert_data = response.json()
            return alert_data.get('resource_uri')

        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating alert: {e}")
            return None

    def calculate_similarity(self, user_query: str, case_texts: List[str]) -> List[float]:
        """Calculate similarity scores between user query and case texts"""
        if not case_texts:
            return []

        # Combine user query with case texts
        all_texts = [user_query] + case_texts

        # Create TF-IDF vectors
        vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        tfidf_matrix = vectorizer.fit_transform(all_texts)

        # Calculate cosine similarity between query and each case
        query_vector = tfidf_matrix[0:1]
        case_vectors = tfidf_matrix[1:]

        similarities = cosine_similarity(query_vector, case_vectors)[0]
        return similarities.tolist()

    def comprehensive_search(self, user_input: str, max_cases: int = 50) -> List[CaseData]:
        """Perform comprehensive search with keyword extraction and expansion"""
        logger.info("=" * 50)
        logger.info("STARTING COMPREHENSIVE SEARCH")
        logger.info("User input: %s", user_input)
        logger.info("Max cases: %d", max_cases)
        logger.info("=" * 50)

        try:
            # Extract keywords
            logger.info("STEP 1: Extracting keywords")
            keywords = self.extract_keywords(user_input)
            logger.info("Extracted keywords: %s", keywords)

            # Expand keywords
            logger.info("STEP 2: Expanding keywords")
            expanded_keywords = self.expand_keywords(keywords)
            logger.info("Expanded keywords count: %d", len(expanded_keywords))
            logger.info("First 10 expanded keywords: %s",
                        expanded_keywords[:10])

            # Search with original query
            logger.info("STEP 3: Searching with original query")
            all_cases = self.search_cases(user_input, limit=max_cases // 3)
            logger.info("Found %d cases with original query", len(all_cases))

            # Search with individual keywords
            logger.info("STEP 4: Searching with individual keywords")
            # Limit to top 5 keywords to avoid rate limits
            for i, keyword in enumerate(keywords[:5]):
                logger.info("Searching with keyword %d/%d: %s",
                            i+1, min(5, len(keywords)), keyword)
                cases = self.search_cases(keyword, limit=max_cases // 6)
                logger.info("Found %d cases with keyword: %s",
                            len(cases), keyword)
                all_cases.extend(cases)
                time.sleep(0.5)  # Rate limiting

            # Search with expanded keywords (sample)
            logger.info("STEP 5: Searching with expanded keywords")
            # Limit to avoid rate limits
            for i, keyword in enumerate(expanded_keywords[:3]):
                if keyword not in keywords:  # Avoid duplicates
                    logger.info("Searching with expanded keyword %d/%d: %s",
                                i+1, min(3, len(expanded_keywords)), keyword)
                    cases = self.search_cases(keyword, limit=max_cases // 6)
                    logger.info(
                        "Found %d cases with expanded keyword: %s", len(cases), keyword)
                    all_cases.extend(cases)
                    time.sleep(0.5)  # Rate limiting

            # Remove duplicates based on resource_uri
            logger.info("STEP 6: Removing duplicates")
            unique_cases = {}
            for case in all_cases:
                if case.resource_uri not in unique_cases:
                    unique_cases[case.resource_uri] = case

            final_cases = list(unique_cases.values())
            logger.info("After deduplication: %d unique cases",
                        len(final_cases))

            # Calculate similarity scores
            logger.info("STEP 7: Calculating similarity scores")
            case_texts = [
                f"{case.case_name} {case.nature_of_suit or ''}" for case in final_cases]
            similarities = self.calculate_similarity(user_input, case_texts)
            logger.info("Calculated similarity scores for %d cases",
                        len(similarities))

            # Sort by similarity score
            logger.info("STEP 8: Sorting by similarity")
            scored_cases = list(zip(final_cases, similarities))
            scored_cases.sort(key=lambda x: x[1], reverse=True)

            # Return top cases
            top_cases = [case for case, score in scored_cases[:max_cases]]
            logger.info("Returning top %d cases", len(top_cases))

            logger.info("=" * 50)
            logger.info("COMPREHENSIVE SEARCH COMPLETED")
            logger.info("Total cases found: %d", len(all_cases))
            logger.info("Unique cases: %d", len(final_cases))
            logger.info("Top cases returned: %d", len(top_cases))
            logger.info("=" * 50)

            return top_cases

        except Exception as e:
            logger.error("Error in comprehensive search: %s", e)
            return []


# Global client instance
courtlistener_client = CourtListenerClient()
