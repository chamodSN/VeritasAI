from crewai import Agent
from langchain_openai import ChatOpenAI
from common.config import Config

llm = ChatOpenAI(model=Config.MODEL_NAME, temperature=Config.TEMPERATURE,
                 api_key=Config.API_KEY, base_url=Config.API_BASE_URL)

summarization_agent = Agent(
    role="Document Summarizer",
    goal="Summarize legal documents concisely using the API.",
    backstory="You create accurate summaries of complex legal texts.",
    llm=llm,
    verbose=True
)