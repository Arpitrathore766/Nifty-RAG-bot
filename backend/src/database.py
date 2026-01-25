from pymongo import MongoClient
import os
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