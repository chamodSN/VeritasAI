import logging
import json
import datetime
import os
from dotenv import load_dotenv
from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from common.config import Config
from transformers import pipeline
import spacy
from rake_nltk import Rake
import requests

# Load environment variables securely
load_dotenv()
Config.API_KEY = os.getenv("COURTLISTENER_API_KEY")
Config.API_BASE_URL = os.getenv("COURTLISTENER_API_BASE_URL")

# Set up logging with detailed configuration
logging.basicConfig(
    filename='summarization_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize LLM with optimized settings
llm = ChatOpenAI(
    model=Config.MODEL_NAME,
    temperature=0.3,  # Lowered for more consistent, factual outputs
    api_key=Config.API_KEY,
    base_url=Config.API_BASE_URL
)

# Initialize NLP tools
nlp = spacy.load("en_core_web_sm")  # For Named Entity Recognition
sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
rake = Rake()  # For keyword extraction

# CourtListener API wrapper
def fetch_case_data(case_id):
    try:
        headers = {"Authorization": f"Token {Config.API_KEY}"}
        response = requests.get(f"{Config.API_BASE_URL}/cases/{case_id}/", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch case {case_id}: {str(e)}")
        return None

# Enhanced bias checking with transformers
def check_summary_bias(summary_text):
    result = sentiment_analyzer(summary_text)[0]
    score = result['score'] if result['label'] == 'POSITIVE' else -result['score']
    if abs(score) > 0.7:  # Stricter threshold for legal neutrality
        return False, f"Warning: Summary may contain biased language (sentiment score: {score:.2f})."
    return True, "Summary appears neutral."

# Enhanced validation with NER and keyword extraction
def validate_summary(summary, case_data):
    doc = nlp(summary)
    entities = {ent.text.lower() for ent in doc.ents if ent.label_ in ["PERSON", "ORG", "GPE", "LAW"]}
    
    # Extract key facts and holdings
    key_facts = case_data.get('facts', '').lower()
    holdings = case_data.get('holdings', '').lower()
    
    # Keyword extraction for validation
    rake.extract_keywords_from_text(key_facts + " " + holdings)
    key_terms = set(rake.get_ranked_phrases()[:5])
    
    # Check if key entities and terms are present
    if not any(term in summary.lower() for term in key_terms):
        return False, "Summary may miss critical case facts or holdings."
    if not any(entity in summary.lower() for entity in entities):
        return False, "Summary may miss key legal entities (e.g., parties, courts)."
    return True, "Summary validated."

# Enhanced logging with structured data
def log_summary(case_id, summary, metadata, bias_message, validation_message):
    log_entry = {
        "case_id": case_id,
        "summary": summary,
        "metadata": metadata,
        "bias_check": bias_message,
        "validation_check": validation_message,
        "timestamp": datetime.datetime.now().isoformat()
    }
    logging.info(json.dumps(log_entry, indent=2))

# Summarization with enhanced Responsible AI features
def generate_summary_with_responsibility(agent, case_id):
    # Fetch case data
    case_data = fetch_case_data(case_id)
    if not case_data:
        return "Error: Could not fetch case data."
    
    # Generate summary with structured instructions
    summary = agent.execute_task(
        task_description=(
            f"Summarize the federal court case (ID: {case_id}) concisely in 150-200 words. "
            "Include:\n"
            "1. Key facts and procedural history\n"
            "2. Legal issues and questions presented\n"
            "3. Court's reasoning and analysis\n"
            "4. Holdings and legal principles established\n"
            "5. Precedential value and significance\n"
            "Use neutral language, avoid legal jargon where possible, and ensure accuracy. "
            f"Case data: {json.dumps(case_data, indent=2)}"
        )
    )
    
    # Extract entities for transparency
    doc = nlp(summary)
    entities = [ent.text for ent in doc.ents if ent.label_ in ["PERSON", "ORG", "GPE", "LAW"]]
    
    # Check for bias
    is_neutral, bias_message = check_summary_bias(summary)
    if not is_neutral:
        logging.warning(f"Bias detected in case {case_id}: {bias_message}")
    
    # Validate summary
    is_valid, validation_message = validate_summary(summary, case_data)
    if not is_valid:
        logging.warning(f"Validation failed for case {case_id}: {validation_message}")
    
    # Log summary with enhanced details
    metadata = {
        "model": Config.MODEL_NAME,
        "temperature": 0.3,
        "entities_detected": entities
    }
    log_summary(case_id, summary, metadata, bias_message, validation_message)
    
    # Add transparency disclaimer
    disclaimer = (
        "\n\n**Transparency Note**: This summary was generated by an AI agent using the CourtListener API and an LLM. "
        "It aims to provide accurate and concise summaries but may not capture all nuances. "
        "Please verify with primary legal sources and consult a legal professional."
    )
    
    # Add explanation with key elements
    explanation = (
        f"\n\n**Explanation**: This summary was generated based on the following key elements:\n"
        f"- Facts: {case_data.get('facts', '')[:100]}...\n"
        f"- Issues: {case_data.get('issues', '')[:100]}...\n"
        f"- Holdings: {case_data.get('holdings', '')[:100]}...\n"
        f"- Entities Detected: {', '.join(entities) if entities else 'None'}"
    )
    
    return summary + disclaimer + explanation

# Define the enhanced summarization agent
summarization_agent = Agent(
    role="Legal Case Summarizer",
    goal="Produce concise, accurate, and neutral summaries of federal court cases from the CourtListener API, adhering to Responsible AI principles.",
    backstory="""You are an expert legal case summarizer with extensive knowledge of:
    - Federal court case law, precedents, and judicial opinions
    - Legal reasoning, case facts, holdings, and principles
    - CourtListener API data structures and legal terminology
    - Responsible AI practices, including bias mitigation and transparency

    Your summaries are:
    - Concise (150-200 words), accurate, and neutral
    - Structured to cover key facts, issues, reasoning, holdings, and precedential value
    - Free of legal jargon where possible, accessible to non-experts
    - Validated for completeness and neutrality using NLP tools
    - Transparent about AI generation and limitations

    You adapt to case complexity, emphasizing landmark cases' significance or simplifying routine cases. You prioritize clarity, neutrality, and actionable legal insights.""",
    llm=llm,
    verbose=True,
    allow_delegation=False  # Prevent delegation to focus on single-agent accuracy
)

# Define the enhanced summarization task
summarization_task = Task(
    description=(
        "Summarize federal court cases from the CourtListener API in 150-200 words, ensuring accuracy, neutrality, and clarity. "
        "Include:\n"
        "- Key facts and procedural history\n"
        "- Legal issues and questions presented\n"
        "- Court's reasoning and analysis\n"
        "- Holdings and legal principles established\n"
        "- Precedential value and significance\n"
        "Use NLP tools (NER, keyword extraction) to validate completeness. "
        "Check for bias using sentiment analysis and ensure neutrality. "
        "Log all outputs with metadata for accountability. "
        "Include a transparency disclaimer and an explanation of key case elements used."
    ),
    agent=summarization_agent,
    expected_output=(
        "A concise (150-200 words), accurate, and neutral summary of a federal court case, covering:\n"
        "- Key facts and procedural history\n"
        "- Legal issues and questions presented\n"
        "- Court's reasoning and analysis\n"
        "- Holdings and legal principles established\n"
        "- Precedential value and significance\n"
        "The summary is validated for neutrality (sentiment analysis) and completeness (NER, keyword extraction). "
        "It includes a transparency disclaimer and an explanation of key case elements (facts, issues, holdings, entities). "
        "All outputs are logged with metadata for accountability."
    ),
    execute=lambda case_id: generate_summary_with_responsibility(summarization_agent, case_id)
)
