Nifty 50 RAG Chatbot
An AI-powered financial assistant that scrapes daily Nifty 50 market data, processes unstructured corporate documents (PDFs), and answers user queries using Agentic RAG (Retrieval-Augmented Generation).

Features
Automated Data Pipeline: Scrapes Nifty 50 live stats and corporate announcements daily using Playwright (bypasses anti-bot protections).
Agentic RAG: Uses LangGraph & Llama 3.3 (70B) to intelligently route queries between:
Vector Search for qualitative questions (e.g., "What did Reliance announce?").
Structured Tools for quantitative math (e.g., "Top 5 gainers").
Prediction Tools for market sentiment analysis.
Dual Database Architecture:
ChromaDB: For vector embeddings of text/PDFs.
MongoDB: For structured market data and ingestion logs.
Full Stack: FastAPI Backend + Streamlit Frontend.

Tech Stack
LLM: Llama 3.3 70B (via Groq API)
Backend: FastAPI, Python 3.10+
Orchestration: LangGraph, LangChain
Databases: MongoDB (Metadata), ChromaDB (Vector)
Scraping: Playwright (Async), BeautifulSoup, PyMuPDF
Frontend: Streamlit

Setup Instructions
1. Prerequisites
Python 3.10+ installed.
Docker Desktop installed (for the database).
Groq API Key (Free) from console.groq.com.

2. Installation
Clone the repository and install dependencies:
Bash
git clone <your-repo-url>
cd nifty_rag_bot

Start the Database (via Docker): Run this command to start a local MongoDB instance instantly:
Bash
docker run -d -p 27017:27017 --name mongo-nifty mongo:latest

# Create virtual environment (Optional but recommended)
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install libraries
pip install -r requirements.txt

# Install Playwright browsers (Required for scraping)
playwright install chromium
3. Configuration (.env)
Create a .env file in the root directory:
# API Keys
GROQ_API_KEY=gsk_your_groq_api_key_here

# Database
# Use "mongodb://localhost:27017/" for local or your Atlas connection string
MONGO_URI=mongodb+srv://<user>:<pass>@cluster0.mongodb.net/?retryWrites=true&w=majority
DB_NAME=nifty_bot
 Usage
You will need two terminal windows to run the full application.

Terminal 1: Start Backend (FastAPI)
Bash
cd backend
python main.py
The API will start at http://localhost:8000.

Terminal 2: Run Data Ingestion
Before chatting, you must populate the database. Run this command while the backend is running:
Bash
# Windows PowerShell
docker run -d -p 27017:27017 --name mongo-nifty mongo:latest  ## to run docker
curl.exe -X POST http://localhost:8000/run-ingestion
# Linux/Mac
curl -X POST http://localhost:8000/run-ingestion
Wait for the "Pipeline Complete" message in Terminal 1.

Just Click on try it out and ask any question


##### No need ###############################
Terminal 3: Start Frontend (Streamlit)
Bash
streamlit run frontend.py
Opens the Chat interface in your browser at http://localhost:8501.
##### -- ####################################
Project Structure
Plaintext
nifty_rag_bot/
├── data/                    # Storage for downloaded PDFs
├── src/
│   ├── agent.py             # LangGraph Agent & Tool definitions
│   ├── scraper.py           # Async Playwright scraper & Data Pipeline
│   ├── database.py          # MongoDB connection logic
│   ├── vector_store.py      # ChromaDB setup & Embedding logic
│   ├── tools.py             # Math & Prediction tools
│   └── models.py            # Pydantic data schemas
├── frontend.py              # Streamlit Chat Interface
├── main.py                  # FastAPI Entry point
├── requirements.txt         # Dependencies
└── README.md                # Documentation

Example Queries
Structured Data: "Who are the top 5 gainers today?"
Unstructured RAG: "What did Reliance announce regarding dividends?"
Prediction: "Predict tomorrow's price for TCS."
