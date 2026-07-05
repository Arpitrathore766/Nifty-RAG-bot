from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.agent import get_agent_executor
from src.scraper import scrape_nse_data
from src.database import save_chat_message, get_chat_history, list_sessions, delete_session
from src.models import QueryRequest, QueryResponse, ChatMessage, SessionInfo
from typing import List
import uvicorn

app = FastAPI(title="Nifty 50 RAG Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501"],  # Allow Next.js & Streamlit
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
        await scrape_nse_data()
        return {"message": "Pipeline executed successfully. Data updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=QueryResponse)
async def chat_endpoint(request: QueryRequest):
    agent = get_agent_executor()
    session_id = request.session_id

    # 1. Save user's question to history
    save_chat_message(session_id, "user", request.query)

    # 2. LangGraph requires input as a "messages" list
    result = agent.invoke({"messages": [("user", request.query)]})

    # 3. The final answer is the last message from the AI
    final_answer = result["messages"][-1].content

    # 4. Save assistant's answer to history
    save_chat_message(session_id, "assistant", final_answer)

    return QueryResponse(answer=final_answer, session_id=session_id)

# ─── Chat History Endpoints ──────────────────────────────────

@app.get("/chat/history/{session_id}", response_model=List[ChatMessage])
async def get_history(session_id: str):
    """Retrieve chat history for a given session."""
    messages = get_chat_history(session_id)
    return messages

@app.get("/chat/sessions", response_model=List[SessionInfo])
async def get_sessions():
    """List all available chat sessions (recent first)."""
    sessions = list_sessions()
    return sessions

@app.delete("/chat/session/{session_id}")
async def delete_session_endpoint(session_id: str):
    """Delete a chat session and its history."""
    delete_session(session_id)
    return {"message": f"Session '{session_id}' deleted."}

# @app.post("/chat", response_model=QueryResponse)
# async def chat(request: QueryRequest):
#     """Chat endpoint for user queries."""
#     try:
#         # LangGraph Input Format: {"messages": [("user", "your query")]}
#         inputs = {"messages": [("user", request.query)]}
        
#         # Invoke the graph
#         result = agent_app.invoke(inputs)
        
#         # Extract the final response from the last message in the conversation
#         final_answer = result["messages"][-1].content
        
#         return QueryResponse(answer=final_answer)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
