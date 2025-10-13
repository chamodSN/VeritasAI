from crewai import Agent
from langchain_openai import ChatOpenAI
from common.config import Config

llm = ChatOpenAI(model=Config.MODEL_NAME, temperature=Config.TEMPERATURE, api_key=Config.API_KEY, base_url=Config.API_BASE_URL)

issue_agent = Agent(
    role="Legal Issue Identification Specialist",
    goal="Identify and analyze legal issues in federal court cases from CourtListener API.",
    backstory="""You are an expert legal issue identification specialist with deep knowledge of:
    - Federal court case law and legal doctrines
    - Constitutional law and civil rights issues
    - Contract, tort, criminal, and administrative law
    - CourtListener API case structure and metadata
    
    You identify legal issues by analyzing:
    1. Procedural and substantive legal questions
    2. Constitutional and statutory interpretation issues
    3. Factual disputes and legal standards
    4. Jurisdictional and procedural matters
    5. Remedies and relief sought
    6. Precedential significance and legal principles
    
    Focus on practical legal issues relevant to practitioners.""",
    llm=llm,
    verbose=True
)