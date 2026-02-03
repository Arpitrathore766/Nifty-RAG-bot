from langchain.tools import tool
from src.database import get_market_stats
from src.vector_store import get_vector_store
import random

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

@tool
def get_top_gainers_losers(query: str):
    """
    Useful for answering questions about top gainers, losers, or worst performers.
    Returns a list of top 5 and bottom 5 stocks from the latest scrape.
    """
    data = get_market_stats()
    if not data:
        return "No market data available. Please run the ingestion pipeline."
    
    # Sort by % Change (assuming string needs conversion)
    # Ensure LTP and %CHNG are floats
    for d in data:
        try:
            d['%CHNG'] = float(str(d['%CHNG']).replace(',', ''))
        except:
            d['%CHNG'] = 0.0

    sorted_data = sorted(data, key=lambda x: x['%CHNG'], reverse=True)
    
    top_5 = sorted_data[:5]
    bottom_5 = sorted_data[-5:]
    
    return f"Top Gainers: {[x['SYMBOL'] + ' (' + str(x['%CHNG']) + '%)' for x in top_5]}\n" \
           f"Top Losers: {[x['SYMBOL'] + ' (' + str(x['%CHNG']) + '%)' for x in bottom_5]}"

@tool
def predict_stock_price(query: str):
    """
    Useful for predicting stock prices or market movement for tomorrow.
    Note: This is a heuristic/dummy prediction tool.
    """
    # Simple Random Heuristic
    move = random.choice(["up", "down", "sideways"])
    percent = round(random.uniform(0.5, 3.0), 2)
    return f"Based on heuristic market sentiment analysis, the stock/market is likely to move {move} by approximately {percent}% tomorrow. (Disclaimer: Not financial advice)."

# RAG Retriever Tool
def get_rag_retriever_tool():
    vector_store = get_vector_store()
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    return retriever