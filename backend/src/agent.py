import os
from langchain_groq import ChatGroq
# from langgraph.prebuilt import create_react_agent
from langchain.agents import create_agent

from src.tools import get_top_gainers_losers, predict_stock_price, get_rag_retriever_tool
from langchain_core.tools import tool # Import generic @tool decorator
from dotenv import load_dotenv

load_dotenv()

# --- Define the Retriever Tool Manually ---
@tool
def search_market_documents(query: str):
    """
    Searches for corporate announcements, reports, and specific stock news.
    Useful when you need to find qualitative info about a company.
    """
    retriever = get_rag_retriever_tool()
    docs = retriever.invoke(query)
    
    # Format the documents into a string for the LLM
    return "\n\n".join([f"[Source: {d.metadata.get('source', 'Unknown')}] {d.page_content}" for d in docs])

def get_agent_executor():
    # 1. Initialize Llama 3.3 70B via Groq
    llm = ChatGroq(
        temperature=0,
        model_name="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY")
    )
    
    # 2. Setup Tools (Use the manual tool created above)
    tools = [search_market_documents, get_top_gainers_losers, predict_stock_price]
    
    # 3. Create Agent (LangGraph)
    agent_app = create_agent(
        model=llm, 
        tools=tools,
        system_prompt="You are a Nifty 50 Market Assistant. Use the available tools to answer financial queries. For 'gainers/losers', ALWAYS use the get_top_gainers_losers tool. For predictions, use the prediction tool."
    )
    
    return agent_app
# import os
# from langchain_groq import ChatGroq
# from langgraph.prebuilt import create_react_agent  # <--- The new standard
# from src.tools import get_top_gainers_losers, predict_stock_price, get_rag_retriever_tool
# # from langchain.tools.retriever import create_retriever_tool
# from langchain.tools import create_retriever_tool
# from dotenv import load_dotenv

# load_dotenv()

# def get_agent_executor():
#     # 1. Initialize Llama 3.3 70B via Groq
#     llm = ChatGroq(
#         temperature=0,
#         model_name="llama-3.3-70b-versatile",
#         api_key=os.getenv("GROQ_API_KEY")
#     )
    
#     # 2. Setup Tools
#     retriever_tool = create_retriever_tool(
#         get_rag_retriever_tool(),
#         "search_market_documents",
#         "Searches for corporate announcements, reports, and specific stock news."
#     )
    
#     tools = [retriever_tool, get_top_gainers_losers, predict_stock_price]
    
#     # 3. Create Agent (LangGraph)
#     # This automatically sets up the tool-calling loop (ReAct pattern)
#     agent_app = create_react_agent(
#         model=llm, 
#         tools=tools,
#         state_modifier="You are a Nifty 50 Market Assistant. Use the available tools to answer financial queries. For 'gainers/losers', ALWAYS use the get_top_gainers_losers tool. For predictions, use the prediction tool."
#     )
    
#     return agent_app