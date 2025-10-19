from crewai import Agent
from langchain_openai import ChatOpenAI
from common.config import Config

llm = ChatOpenAI(model=Config.MODEL_NAME, temperature=Config.TEMPERATURE,
                 api_key=Config.API_KEY, base_url=Config.API_BASE_URL)

summarization_agent = Agent(
    role="Legal Case Summarizer",
    goal="Summarize federal court cases from CourtListener API concisely and accurately.",
    backstory="""You are an expert legal case summarizer with deep knowledge of:
    - Federal court case law and precedents
    - Legal reasoning and judicial opinions
    - Case facts, holdings, and legal principles
    - CourtListener API case data structure
    
    You create comprehensive yet concise summaries that highlight:
    1. Key facts and procedural history
    2. Legal issues and questions presented
    3. Court's reasoning and analysis
    4. Holdings and legal principles established
    5. Precedential value and significance
    
    Focus on accuracy, clarity, and practical legal insights.""",
    llm=llm,
    verbose=True
)