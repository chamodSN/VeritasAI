from crewai import Agent
from  langchain_openai import ChatOpenAI
from common.config import Config

llm = ChatOpenAI(model=Config.MODEL_NAME, temperature=Config.TEMPERATURE, api_key=Config.API_KEY, base_url=Config.API_BASE_URL)

issue_agent = Agent(
    role="Legal Issue Spotter",
    goal="Identify and tag legal issues in documents using the API.",
    backstory="You are trained to spot key legal issues, doctrines, and precedents.",
    llm=llm,
    verbose=True
)