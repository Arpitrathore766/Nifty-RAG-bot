import os
from langchain_groq import ChatGroq
# from langgraph.prebuilt import create_react_agent
from langchain.agents import create_agent

from src.tools import get_top_gainers_losers, predict_stock_price, search_market_documents
from langchain_core.tools import tool # Import generic @tool decorator
from dotenv import load_dotenv

load_dotenv()

def get_agent_executor():
    # 1. Initialize Llama 3.3 70B via Groq
    llm = ChatGroq(
        temperature=0,
        model_name="llama-3.3-70b-versatile",
        # model_name="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY")
    )
    
    # 2. Setup Tools (Use the manual tool created above)
    tools = [search_market_documents, get_top_gainers_losers, predict_stock_price]
    
    # # 3. Create Agent (LangGraph)
    # agent_app = create_agent(
    #     model=llm, 
    #     tools=tools,
    #     system_prompt=(
    #     "You are a Nifty 50 Market Assistant. "
    #     "Use search_market_documents for: company news, announcements, stock price queries, dividend info. "
    #     "Use get_top_gainers_losers for: top gainers, top losers, market movers. "
    #     "Use predict_stock_price for: price predictions, tomorrow's forecast."
    # )
    # )
    agent_app = create_agent(llm, tools)
    
    return agent_app
