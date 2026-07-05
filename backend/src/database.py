from pymongo import MongoClient
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db = client[os.getenv("DB_NAME", "nifty_bot")]

def log_ingestion(data):
    """Log every pipeline run."""
    db.ingestion_logs.insert_one(data)

def save_market_stats(data_list):
    """Save structured market data (gainers/losers) for math queries."""
    # Clear old daily stats to keep 'today' fresh
    db.market_stats.delete_many({})
    if data_list:
        db.market_stats.insert_many(data_list)

def get_market_stats():
    return list(db.market_stats.find({}, {"_id": 0}))


# ─── Chat History ───────────────────────────────────────────────

def save_chat_message(session_id: str, role: str, content: str):
    """Save a single chat message to the session history."""
    db.chat_history.insert_one({
        "session_id": session_id,
        "role": role,          # "user" or "assistant"
        "content": content,
        "timestamp": datetime.now()
    })

def get_chat_history(session_id: str, limit: int = 100):
    """Retrieve all messages for a session, oldest first."""
    cursor = db.chat_history.find(
        {"session_id": session_id},
        {"_id": 0, "session_id": 0}
    ).sort("timestamp", 1).limit(limit)
    return list(cursor)

def list_sessions(limit: int = 20):
    """List recent distinct session IDs with their last message timestamp."""
    pipeline = [
        {"$sort": {"timestamp": -1}},
        {"$group": {
            "_id": "$session_id",
            "last_active": {"$first": "$timestamp"},
            "message_count": {"$sum": 1}
        }},
        {"$sort": {"last_active": -1}},
        {"$limit": limit}
    ]
    results = list(db.chat_history.aggregate(pipeline))
    return [
        {
            "session_id": r["_id"],
            "last_active": r["last_active"],
            "message_count": r["message_count"]
        }
        for r in results
    ]

def delete_session(session_id: str):
    """Delete all messages for a given session."""
    db.chat_history.delete_many({"session_id": session_id})