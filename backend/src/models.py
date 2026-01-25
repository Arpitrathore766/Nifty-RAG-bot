from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# --- API Request/Response Models ---
# Used by FastAPI in main.py
class QueryRequest(BaseModel):
    query: str = Field(..., description="The user's question about Nifty 50 data.")

class QueryResponse(BaseModel):
    answer: str
    timestamp: datetime = Field(default_factory=datetime.now)

# --- Database / Scraping Models ---
# Used to validate scraped data before inserting into MongoDB
class StockRecord(BaseModel):
    symbol: str
    open: float
    high: float
    low: float
    ltp: float        # Last Traded Price
    change_percent: float
    volume: int
    date: str         # ISO Format YYYY-MM-DD

class IngestionLog(BaseModel):
    status: str       # "success" or "failed"
    items_scraped: int
    errors: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.now)