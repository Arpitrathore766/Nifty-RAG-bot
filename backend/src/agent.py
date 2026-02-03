# import os
# from langchain_groq import ChatGroq
# # from langchain.agents import create_react_agent, AgentExecutor
# # from langchain.agents.react.agent import create_react_agent
# from langgraph.prebuilt import create_react_agent

# from langchain.agents import AgentExecutor

# from langchain_core.prompts import PromptTemplate
# from src.tools import get_top_gainers_losers, predict_stock_price, search_market_documents
# from dotenv import load_dotenv

# load_dotenv()

# def get_agent_executor():
#     # 1. Initialize Llama 3.3 via Groq
#     llm = ChatGroq(
#         temperature=0,
#         model_name="llama-3.3-70b-versatile",
#         api_key=os.getenv("GROQ_API_KEY")
#     )
    
#     # 2. Define the Tools List
#     # Ensure these are the actual function objects imported from tools.py
#     tools = [search_market_documents, get_top_gainers_losers, predict_stock_price]
    
#     # 3. Define the ReAct Prompt Template
#     # This acts as the "System Prompt" and teaches the model exactly how to use tools
#     template = """
#     You are a Nifty 50 Market Assistant. Answer the following questions as best you can.
    
#     For questions about "price", "news", "announcements", or "option chain", use the tool: search_market_documents.
#     For questions about "gainers" or "losers", use the tool: get_top_gainers_losers.
#     For predictions, use the tool: predict_stock_price.

#     You have access to the following tools:

#     {tools}

#     Use the following format:

#     Question: the input question you must answer
#     Thought: you should always think about what to do
#     Action: the action to take, should be one of [{tool_names}]
#     Action Input: the input to the action
#     Observation: the result of the action
#     ... (this Thought/Action/Action Input/Observation can repeat N times)
#     Thought: I now know the final answer
#     Final Answer: the final answer to the original input question

#     Begin!

#     Question: {input}
#     Thought: {agent_scratchpad}
#     """
    
#     prompt = PromptTemplate.from_template(template)

#     # 4. Create the Agent
#     agent = create_react_agent(llm, tools, prompt)

#     # 5. Create the Executor (The Runtime)
#     # handle_parsing_errors=True is CRITICAL. It catches formatting mistakes and retries instead of crashing.
#     agent_executor = AgentExecutor(
#         agent=agent, 
#         tools=tools, 
#         verbose=True, 
#         handle_parsing_errors=True
#     )
    
#     return agent_executor
import os
from langchain_groq import ChatGroq
# from langgraph.prebuilt import create_react_agent
from langchain.agents import create_agent

from src.tools import get_top_gainers_losers, predict_stock_price, search_market_documents
from langchain_core.tools import tool # Import generic @tool decorator
from dotenv import load_dotenv

load_dotenv()

# --- Define the Retriever Tool Manually ---
# @tool
# def search_market_documents(query: str):
#     """
#     Searches for corporate announcements, reports, and specific stock news.
#     Useful when you need to find qualitative info about a company.
#     """
#     retriever = get_rag_retriever_tool()
#     docs = retriever.invoke(query)
    
#     # Format the documents into a string for the LLM
#     return "\n\n".join([f"[Source: {d.metadata.get('source', 'Unknown')}] {d.page_content}" for d in docs])

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
    
    # 3. Create Agent (LangGraph)
    agent_app = create_agent(
        model=llm, 
        tools=tools,
        system_prompt="You are a Nifty 50 Market Assistant. Use the available tools to answer financial queries. For 'gainers/losers', ALWAYS use the get_top_gainers_losers tool. For predictions, use the prediction tool. Also use search_market_documents for answering queries"
    )
    agent_app = create_agent(llm, tools)
    
    return agent_app
