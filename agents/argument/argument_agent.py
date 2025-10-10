from crewai import Agent
from langchain_openai import ChatOpenAI
from common.config import Config

llm = ChatOpenAI(model=Config.MODEL_NAME, temperature=Config.TEMPERATURE,
                 api_key=Config.API_KEY, base_url=Config.API_BASE_URL)

argument_agent = Agent(
    role="Argumentation & Counterargument Generator",
    goal="Generate legal arguments and counterarguments based on precedents using the API.",
    backstory="You build strong legal arguments by analyzing cases and doctrines.",
    llm=llm,
    verbose=True
)
