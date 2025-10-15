import logging
import pandas as pd
import json
import datetime
import os
from dotenv import load_dotenv
from typing import Dict, List, Any
from crewai import Agent
from crewai.tools import BaseTool
from langchain_openai import ChatOpenAI
from common.config import Config
import spacy
from transformers import pipeline
from rake_nltk import Rake
import requests
from scipy import stats

# Load environment variables securely
load_dotenv()
Config.API_KEY = os.getenv("COURTLISTENER_API_KEY")
Config.API_BASE_URL = os.getenv("COURTLISTENER_API_BASE_URL")

# Configure logging with detailed format
logging.basicConfig(
    filename='analytics_agent_log.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)

# Initialize LLM with optimized settings
llm = ChatOpenAI(
    model=Config.MODEL_NAME,
    temperature=0.2,  # Lowered for factual, consistent outputs
    api_key=Config.API_KEY,
    base_url=Config.API_BASE_URL
)

# Initialize NLP tools
nlp = spacy.load("en_core_web_sm")  # For Named Entity Recognition
sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
rake = Rake()  # For keyword extraction

# CourtListener API wrapper
class CourtListenerAPI:
    @staticmethod
    def fetch_case_data(query_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        try:
            headers = {"Authorization": f"Token {Config.API_KEY}"}
            url = f"{Config.API_BASE_URL}/cases/"
            response = requests.get(url, headers=headers, params=query_params)
            response.raise_for_status()
            return response.json().get('results', [])
        except requests.RequestException as e:
            logging.error(f"Failed to fetch case data: {str(e)}")
            return []

# Enhanced Responsible AI utilities
class ResponsibleAIAnalytics:
    @staticmethod
    def check_for_bias(data: List[Dict[str, Any]], sensitive_attributes: List[str] = None) -> Dict[str, Any]:
        try:
            if not sensitive_attributes:
                sensitive_attributes = ['jurisdiction', 'case_type', 'party_demographics']
            df = pd.DataFrame(data)
            bias_report = {}
            for attr in sensitive_attributes:
                if attr in df.columns and 'outcome' in df.columns:
                    # Statistical test for bias (e.g., chi-squared)
                    contingency_table = pd.crosstab(df[attr], df['outcome'])
                    chi2, p_value, _, _ = stats.chi2_contingency(contingency_table)
                    outcome_dist = df.groupby(attr)['outcome'].value_counts(normalize=True).to_dict()
                    bias_report[attr] = {
                        "distribution": outcome_dist,
                        "chi2_p_value": p_value,
                        "potential_bias": p_value < 0.05  # Significant at 5% level
                    }
                    logging.info(f"Bias check for {attr}: {bias_report[attr]}")
            return {
                "bias_detected": any(r["potential_bias"] for r in bias_report.values()),
                "details": bias_report,
                "recommendation": "Review attributes with p-value < 0.05 for potential bias mitigation."
            }
        except Exception as e:
            logging.error(f"Bias check failed: {str(e)}")
            return {"bias_detected": False, "details": {}, "error": str(e)}

    @staticmethod
    def anonymize_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        anonymized_data = []
        sensitive_fields = ['party_name', 'personal_identifier', 'address', 'ssn', 'phone']
        for item in data:
            anon_item = item.copy()
            doc = nlp(json.dumps(anon_item))  # Use NER to detect additional sensitive entities
            entities = {ent.text for ent in doc.ents if ent.label_ in ["PERSON", "GPE"]}
            for field in sensitive_fields:
                if field in anon_item:
                    anon_item[field] = 'REDACTED'
            for entity in entities:
                for key in anon_item:
                    if isinstance(anon_item[key], str):
                        anon_item[key] = anon_item[key].replace(entity, 'REDACTED')
            anonymized_data.append(anon_item)
        logging.info("Data anonymization completed with NER.")
        return anonymized_data

    @staticmethod
    def generate_explanation(analysis_results: Dict[str, Any]) -> str:
        # Extract keywords from results for clarity
        rake.extract_keywords_from_text(analysis_results.get('summary', ''))
        key_terms = rake.get_ranked_phrases()[:5]
        explanation = (
            "Analysis performed using CourtListener API data.\n"
            f"Data sources: Case metadata (jurisdiction, case type, outcomes, citations).\n"
            f"Methodology: Statistical analysis (chi-squared tests, trend analysis) and NLP (entity recognition, keyword extraction).\n"
            f"Key Findings: {analysis_results.get('summary', 'No summary available.')}\n"
            f"Key Terms: {', '.join(key_terms) if key_terms else 'None'}\n"
            f"Limitations: Potential gaps in API data; bias checks limited to available attributes.\n"
            "Transparency: Results validated for neutrality and logged in analytics_agent_log.log."
        )
        logging.info("Explanation generated for analysis results.")
        return explanation

# Define custom tools
class BiasCheckTool(BaseTool):
    name: str = "Bias Check Tool"
    description: str = (
        "Analyzes case data for potential biases in outcomes based on sensitive attributes (e.g., jurisdiction, case type). "
        "Uses statistical tests (chi-squared) and logs results for accountability."
    )

    def _run(self, data: List[Dict[str, Any]], sensitive_attributes: List[str] = None) -> Dict[str, Any]:
        return ResponsibleAIAnalytics.check_for_bias(data, sensitive_attributes)

class AnonymizeDataTool(BaseTool):
    name: str = "Data Anonymization Tool"
    description: str = (
        "Anonymizes sensitive fields (e.g., party names, identifiers) in case metadata using NER and predefined rules "
        "to ensure privacy compliance."
    )

    def _run(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return ResponsibleAIAnalytics.anonymize_data(data)

class ExplanationTool(BaseTool):
    name: str = "Analysis Explanation Tool"
    description: str = (
        "Generates a human-readable explanation of the legal analysis process, including data sources, methodology, "
        "key terms, and limitations."
    )

    def _run(self, analysis_results: Dict[str, Any]) -> str:
        return ResponsibleAIAnalytics.generate_explanation(analysis_results)

class StatisticalAnalysisTool(BaseTool):
    name: str = "Statistical Analysis Tool"
    description: str = (
        "Performs statistical analysis on case data to identify trends, correlations, and patterns "
        "(e.g., outcome frequency, jurisdictional trends)."
    )

    def _run(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            df = pd.DataFrame(data)
            if df.empty:
                return {"error": "No data available for analysis."}
            
            # Example: Analyze outcome frequency by jurisdiction
            trends = {
                "jurisdiction_outcomes": df.groupby('jurisdiction')['outcome'].value_counts(normalize=True).to_dict(),
                "case_type_counts": df['case_type'].value_counts().to_dict(),
                "temporal_trends": df.groupby(df['date'].str[:4])['outcome'].count().to_dict() if 'date' in df.columns else {}
            }
            
            # Correlation analysis (example: case duration vs. outcome)
            if 'duration' in df.columns and 'outcome' in df.columns:
                df['outcome_binary'] = df['outcome'].map({'granted': 1, 'denied': 0}).fillna(0)
                correlation, _ = stats.pearsonr(df['duration'].fillna(0), df['outcome_binary'])
                trends['duration_outcome_correlation'] = correlation
            
            logging.info(f"Statistical analysis results: {trends}")
            return {"trends": trends, "summary": "Statistical analysis completed successfully."}
        except Exception as e:
            logging.error(f"Statistical analysis failed: {str(e)}")
            return {"error": str(e)}

# Define the enhanced Legal Case Pattern Analyzer Agent
analytics_agent = Agent(
    role="Legal Case Pattern Analyzer",
    goal=(
        "Analyze patterns, trends, and insights across federal court cases from the CourtListener API "
        "with a focus on fairness, transparency, and privacy, adhering to Responsible AI principles."
    ),
    backstory="""You are an expert legal analytics specialist with extensive expertise in:
    - Federal court case law, judicial trends, and precedent evolution
    - Statistical analysis of case metadata (jurisdiction, case type, outcomes)
    - Citation networks and legal doctrine development
    - Responsible AI practices, including bias detection, data privacy, and transparency
    
    You analyze legal patterns by:
    1. Identifying jurisdictional and temporal trends in case outcomes
    2. Mapping citation networks to assess precedent influence
    3. Analyzing case type frequency and resolution patterns
    4. Detecting potential biases in outcomes using statistical and NLP methods
    5. Providing actionable insights for legal research and strategy
    
    You ensure Responsible AI by:
    - Using NLP (NER, keyword extraction) and statistical tests for robust analysis
    - Mitigating biases through rigorous checks and validation
    - Anonymizing sensitive data to protect privacy
    - Providing transparent explanations of methodology and limitations
    - Logging all actions for accountability
    
    You adapt to case complexity, emphasizing landmark cases' influence or simplifying routine patterns, while maintaining ethical standards.""",
    llm=llm,
    verbose=True,
    tools=[
        BiasCheckTool(),
        AnonymizeDataTool(),
        ExplanationTool(),
        StatisticalAnalysisTool()
    ],
    max_iterations=15,  # Increased for complex analyses
    memory=True,
    allow_delegation=False
)