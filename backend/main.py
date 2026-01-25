from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.agent import get_agent_executor
from src.scraper import scrape_nse_data
from src.models import QueryRequest, QueryResponse
import uvicorn

app = FastAPI(title="Nifty 50 RAG Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow Next.js
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Initialize LangGraph Agent
agent_app = get_agent_executor()

@app.post("/run-ingestion")
async def run_pipeline():
    """Trigger the scraping and ingestion pipeline manually."""
    try:
        await scrape_nse_data()  # <--- CHANGED: Added 'await'
        return {"message": "Pipeline executed successfully. Data updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=QueryResponse)
async def chat(request: QueryRequest):
    """Chat endpoint for user queries."""
    try:
        # LangGraph Input Format: {"messages": [("user", "your query")]}
        inputs = {"messages": [("user", request.query)]}
        
        # Invoke the graph
        result = agent_app.invoke(inputs)
        
        # Extract the final response from the last message in the conversation
        final_answer = result["messages"][-1].content
        
        return QueryResponse(answer=final_answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
