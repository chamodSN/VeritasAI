"""
CourtListener API v4 Client for Legal Case Research
Handles keyword extraction, expansion, and case data retrieval
"""

import time
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from common.config import Config
from common.logging import logger
import spacy
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from model.legal_term_expander import legal_term_expander

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
    cluster_id: str
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
        """Search for cases using CourtListener API with enhanced data cleaning"""
        logger.info("Searching cases with query: '%s', limit: %d", query, limit)

        url = f"{self.base_url}/search/"
        params = {
            'q': query,
            'stat_Precedential': 'on',
            'order_by': 'score desc',
            'stat_Non-Precedential': 'on',
            'format': 'json',
            'stat_Errata': 'on',  # Include errata
            'stat_Separate': 'on',  # Include separate opinions
            'stat_In-chambers': 'on'  # Include in-chambers opinions
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
            results = data.get('results', [])
            logger.info("Found %d results in API response", len(results))

            cases = []
            for i, result in enumerate(results[:limit]):
                
                # Clean case data
                case_name = self._clean_text(result.get('caseName', ''))
                court = self._clean_text(result.get('court', ''))
                nature_of_suit = self._clean_text(result.get('natureOfSuit', ''))
                
                case_data = CaseData(
                    case_name=case_name,
                    court=court,
                    date_filed=result.get('dateFiled', ''),
                    date_modified=result.get('dateModified', ''),
                    absolute_url=result.get('absolute_url', ''),
                    resource_uri=result.get('resource_uri', ''),
                    cluster_id=str(result.get('cluster_id', '')),
                    docket_number=result.get('docketNumber', ''),
                    citation_count=result.get('citationCount', 0),
                    precedential=result.get('precedential', False),
                    nature_of_suit=nature_of_suit,
                    jurisdiction=result.get('jurisdiction', '')
                )
                cases.append(case_data)

            return cases

        except requests.exceptions.RequestException as e:
            logger.error("Request error searching cases: %s", e)
            return []
        except Exception as e:
            logger.error("Unexpected error searching cases: %s", e)
            return []

    def _clean_text(self, text: str) -> str:
        """Clean text by removing HTML tags, extra whitespace, and unnecessary characters"""
        if not text:
            return ""
        
        import re
        
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

    def get_case_text(self, case_id: str) -> str:
        """Get cleaned case text from CourtListener API"""
        try:
            # First get the case details
            case_url = f"{self.base_url}/clusters/{case_id}/"
            response = requests.get(case_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            case_data = response.json()
            
            # Get opinions for this case
            opinions_url = f"{self.base_url}/opinions/"
            opinions_params = {
                'cluster': case_id,
                'format': 'json'
            }
            
            opinions_response = requests.get(
                opinions_url, headers=self.headers, params=opinions_params, timeout=30)
            opinions_response.raise_for_status()
            
            opinions_data = opinions_response.json()
            opinions = opinions_data.get('results', [])
            
            # Combine all opinion text
            combined_text = ""
            for opinion in opinions:
                # Try different text fields
                text_content = None
                if 'plain_text' in opinion and opinion['plain_text']:
                    text_content = opinion['plain_text']
                elif 'text' in opinion and opinion['text']:
                    text_content = opinion['text']
                elif 'html' in opinion and opinion['html']:
                    text_content = opinion['html']
                
                if text_content:
                    # Clean the opinion text
                    cleaned_text = self._clean_text(text_content)
                    if cleaned_text:
                        combined_text += f"\n\n{cleaned_text}"
            
            # If no opinions found, try to get casebody
            if not combined_text and 'casebody' in case_data:
                casebody_url = case_data['casebody']
                casebody_response = requests.get(
                    casebody_url, headers=self.headers, timeout=30)
                if casebody_response.status_code == 200:
                    casebody_data = casebody_response.json()
                    if 'text' in casebody_data:
                        combined_text = self._clean_text(casebody_data['text'])
            
            return combined_text
            
        except Exception as e:
            logger.error(f"Error getting case text for {case_id}: {e}")
            return ""

    def get_multiple_cases_text(self, case_ids: List[str]) -> Dict[str, str]:
        """Get text for multiple cases efficiently"""
        case_texts = {}
        
        for case_id in case_ids:
            try:
                text = self.get_case_text(case_id)
                if text and len(text.strip()) > 100:  # Only include cases with substantial text
                    case_texts[case_id] = text
                else:
                    logger.warning(f"Case {case_id} has insufficient text ({len(text)} chars)")
            except Exception as e:
                logger.error(f"Error processing case {case_id}: {e}")
                continue
                
        return case_texts

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
            keywords = self.extract_keywords(user_input)
            logger.info("Extracted keywords: %s", keywords)

            # Expand keywords
            expanded_keywords = self.expand_keywords(keywords)
            logger.info("Expanded keywords count: %d", len(expanded_keywords))

            # Search with original query
            original_limit = max(1, max_cases // 2)
            all_cases = self.search_cases(user_input, limit=original_limit)
            logger.info("Found %d cases with original query", len(all_cases))

            # Search with individual keywords
            # Limit to top 5 keywords to avoid rate limits
            keyword_limit = max(1, max_cases // 8)
            for i, keyword in enumerate(keywords[:5]):
                cases = self.search_cases(keyword, limit=keyword_limit)
                all_cases.extend(cases)
                time.sleep(0.5)  # Rate limiting

            # Search with expanded keywords (sample)
            # Limit to avoid rate limits
            for i, keyword in enumerate(expanded_keywords[:3]):
                if keyword not in keywords:  # Avoid duplicates
                    logger.info("Searching with expanded keyword %d/%d: %s",
                                i+1, min(3, len(expanded_keywords)), keyword)
                    cases = self.search_cases(keyword, limit=keyword_limit)
                    logger.info(
                        "Found %d cases with expanded keyword: %s", len(cases), keyword)
                    all_cases.extend(cases)
                    time.sleep(0.5)  # Rate limiting

            # Remove duplicates based on resource_uri
            unique_cases = {}
            for case in all_cases:
                if case.resource_uri not in unique_cases:
                    unique_cases[case.resource_uri] = case

            final_cases = list(unique_cases.values())
            logger.info("After deduplication: %d unique cases",
                        len(final_cases))

            # Filter cases by quality metrics
            quality_cases = []
            for case in final_cases:
                # Prioritize precedential cases
                if case.precedential:
                    quality_cases.append((case, 1.0))
                # Include cases with substantial citation count
                elif case.citation_count and case.citation_count > 5:
                    quality_cases.append((case, 0.8))
                # Include recent cases (last 10 years)
                elif case.date_filed and '2020' <= case.date_filed[:4] <= '2024':
                    quality_cases.append((case, 0.6))
                else:
                    quality_cases.append((case, 0.4))

            # Sort by quality score
            quality_cases.sort(key=lambda x: x[1], reverse=True)
            filtered_cases = [case for case, score in quality_cases]

            # Calculate similarity scores
            case_texts = [
                f"{case.case_name} {case.nature_of_suit or ''}" for case in filtered_cases]
            similarities = self.calculate_similarity(user_input, case_texts)
            logger.info("Calculated similarity scores for %d cases",
                        len(similarities))

            # Sort by similarity score
            scored_cases = list(zip(filtered_cases, similarities))
            scored_cases.sort(key=lambda x: x[1], reverse=True)

            # Return top cases
            top_cases = [case for case, score in scored_cases[:max_cases]]
            logger.info("Returning top %d cases", len(top_cases))

            logger.info("=" * 50)
            logger.info("COMPREHENSIVE SEARCH COMPLETED")
            logger.info("Total cases found: %d", len(all_cases))
            logger.info("Unique cases: %d", len(final_cases))
            logger.info("Quality filtered cases: %d", len(filtered_cases))
            logger.info("Top cases returned: %d", len(top_cases))
            logger.info("=" * 50)

            return top_cases

        except Exception as e:
            logger.error("Error in comprehensive search: %s", e)
            return []


# Global client instance
courtlistener_client = CourtListenerClient()
