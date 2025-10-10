from crewai import Agent
from langchain_openai import ChatOpenAI
from common.config import Config

llm = ChatOpenAI(model=Config.MODEL_NAME, temperature=Config.TEMPERATURE,
                 api_key=Config.API_KEY, base_url=Config.API_BASE_URL)

analytics_agent = Agent(
    role="Case Pattern Analyzer",
    goal="Detect trends and patterns in legal cases using the API (optional).",
    backstory="You analyze patterns across multiple cases for insights.",
    llm=llm,
    verbose=True
)