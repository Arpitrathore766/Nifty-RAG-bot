# Nifty 50 RAG Chatbot — High-Level Design (HLD)

> **AI-Powered Financial Assistant** | Agentic RAG · Llama 3.3 70B · Real-time NSE Data

---

## 1. System Overview

The Nifty 50 RAG Chatbot is an **Agentic Retrieval-Augmented Generation (RAG)** system that scrapes live NSE market data, stores it in a dual-database architecture, and answers user queries through an LLM-powered agent that intelligently routes questions to the right tool.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            SYSTEM ARCHITECTURE                           │
└──────────────────────────────────────────────────────────────────────────┘

                            ┌─────────────────┐
                            │    User (Browser) │
                            └────────┬────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                │
            ┌──────────────┐  ┌──────────────┐       │
            │  Streamlit   │  │  FastAPI      │       │
            │  Frontend    │  │  Swagger UI   │       │
            │  (:8501)     │  │  (:8000/docs) │       │
            └──────┬───────┘  └──────┬────────┘       │
                   │                 │                 │
                   └────────┬────────┘                 │
                            │ HTTP POST /chat           │
                            ▼                           │
              ┌─────────────────────────┐               │
              │     FastAPI Backend      │               │
              │       (main.py)          │               │
              │   ┌───────────────────┐  │               │
              │   │  /chat             │  │               │
              │   │  /run-ingestion    │  │               │
              │   └───────────────────┘  │               │
              └────────────┬─────────────┘               │
                           │                             │
              ┌────────────┼─────────────┐               │
              │            │             │               │
              ▼            ▼             ▼               │
    ┌─────────────┐ ┌───────────┐ ┌───────────┐         │
    │  LangGraph   │ │  Scraper  │ │  Models   │         │
    │  Agent       │ │  Pipeline │ │ (Pydantic)│         │
    │ (agent.py)   │ │(scraper.py)│ │           │         │
    └──────┬───────┘ └─────┬─────┘ └───────────┘         │
           │               │                              │
           │         ┌─────┴─────┐                        │
           │         │  Selenium │                        │
           │         │  + yFinance│                       │
           │         │  (Fallback)│                       │
           │         └─────┬─────┘                        │
           │               │                              │
    ┌──────┴───────┐       │                              │
    │              │       │                              │
    ▼              ▼       ▼                              │
┌─────────┐  ┌─────────┐  ┌─────────┐                    │
│  Groq   │  │ChromaDB │  │ MongoDB │                    │
│  API    │  │(Vector  │  │(Structured                   │
│ Llama   │  │ Store)  │  │  Data)  │                    │
│3.3 70B  │  │         │  │         │                    │
└─────────┘  └─────────┘  └─────────┘                    │
    │              │             │                        │
    │  Embeddings  │             │                        │
    │  Model:      │             │                        │
    │  all-MiniLM  │             │                        │
    │  -L6-v2      │             │                        │
    └──────────────┘             │                        │
                                 │                        │
```

---

## 2. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **LLM** | Llama 3.3 70B (via Groq API) | Reasoning, tool selection, answer synthesis |
| **Agent Framework** | LangChain + LangGraph | Agent orchestration, tool binding, conversation management |
| **Embeddings** | `all-MiniLM-L6-v2` (HuggingFace, local) | Convert text → 384-dim vectors for semantic search |
| **Vector DB** | ChromaDB (persistent) | Store & retrieve embedded market documents |
| **Metadata DB** | MongoDB | Store structured stock data (LTP, OHLC, volume) |
| **Backend** | FastAPI + Uvicorn | REST API server |
| **Frontend** | Streamlit | Chat UI |
| **Scraping** | Selenium + ChromeDriver 
| **Fallback Data** | Yahoo Finance (`yfinance`) | Backup when NSE blocks scraping |
| **Validation** | Pydantic | Request/response schema validation |

---

## 3. Dual-Database Architecture

### Why Two Databases?

```
┌─────────────────────────────────────────────────────────────────┐
│                    DUAL DATABASE STRATEGY                        │
├────────────────────────────┬────────────────────────────────────┤
│        MongoDB              │          ChromaDB                  │
│     (Structured Data)       │       (Vector Store)               │
├─────────────────────────────┼────────────────────────────────────┤
│                             │                                    │
│  • Exact numeric queries    │  • Semantic search                 │
│  • Sorting, filtering       │  • "Find me news about X"         │
│  • Top gainers/losers       │  • Unstructured document search    │
│  • Stock-by-symbol lookup   │  • Corporate announcements         │
│                             │                                    │
│  Collection: market_stats   │  Collection: nifty_data            │
│  ┌──────────────────────┐   │  ┌────────────────────────────┐   │
│  │ SYMBOL │ LTP  │ %CHNG│   │  │ "Stock Update: TCS.        │   │
│  │ TCS    │ 2070 │ +1.2 │   │  │  Current Price: 2070..."    │   │
│  │ INFY   │ 1600 │ -0.5 │   │  │              ↓              │   │
│  └──────────────────────┘   │  │   384-dim vector embedding  │   │
│                             │  └────────────────────────────┘   │
│  Used by:                   │  Used by:                         │
│  get_top_gainers_losers()   │  search_market_documents()        │
└─────────────────────────────┴────────────────────────────────────┘
```

**Design Rationale:** Financial queries come in two flavors:
- **Quantitative** ("Top 5 gainers", "TCS price") → Needs exact numbers, sorting → **MongoDB**
- **Qualitative** ("What did Reliance announce?", "Dividend news") → Needs semantic understanding → **ChromaDB**

---

## 4. Agentic RAG Architecture

### What Makes It "Agentic"?

Traditional RAG is a fixed pipeline: embed query → retrieve docs → feed to LLM → answer. **Agentic RAG** gives the LLM control over *which* tool to call, *when* to call it, and *how* to synthesize the result.

```
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT DECISION LOOP                         │
└─────────────────────────────────────────────────────────────────┘

    User: "What is TCS stock price today?"
                │
                ▼
    ┌────────────────────────┐
    │   LangGraph Agent       │
    │   (Llama 3.3 70B)       │
    │                         │
    │  System Prompt:         │
    │  "You are a Nifty 50    │
    │   Market Assistant..."  │
    └───────────┬─────────────┘
                │
                │  LLM decides: "This is a stock price query..."
                │
                ▼
    ┌───────────────────────────────────────┐
    │          TOOL SELECTION                │
    │                                        │
    │  ┌─────────────────────────────────┐   │
    │  │ search_market_documents(query)  │◄──│─── Qualitative Q's
    │  │  → ChromaDB vector search       │   │    "What did Reliance announce?"
    │  └─────────────────────────────────┘   │
    │                                        │
    │  ┌─────────────────────────────────┐   │
    │  │ get_top_gainers_losers(query)   │◄──│─── Market movers
    │  │  → MongoDB sort by %CHNG        │   │    "Top 5 gainers today?"
    │  └─────────────────────────────────┘   │
    │                                        │
    │  ┌─────────────────────────────────┐   │
    │  │ predict_stock_price(query)      │◄──│─── Forecasts
    │  │  → Heuristic analysis           │   │    "Predict TCS tomorrow"
    │  └─────────────────────────────────┘   │
    └───────────────────┬───────────────────┘
                        │
                        ▼
    ┌───────────────────────────────────────┐
    │        LLM SYNTHESIZES ANSWER          │
    │                                        │
    │  Tool returns raw data →               │
    │  LLM formats into natural language     │
    │  "TCS is currently trading at ₹2,070,  │
    │   up 1.2% today with volume of 2.3M." │
    └───────────────────────────────────────┘
```

### Agent Execution Flow (LangGraph)

```
messages = [("user", "What is TCS price?")]
    │
    ▼
agent.invoke(messages)
    │
    ▼
LLM analyzes query + available tools
    │
    ├──→ Decides: search_market_documents("TCS stock price")
    │       │
    │       ▼
    │    ChromaDB similarity search (k=3)
    │       │
    │       ▼
    │    Returns relevant document chunks
    │
    ▼
LLM receives tool output → generates final answer
    │
    ▼
Response: {"answer": "TCS is trading at ₹2,070..."}
```

---

## 5. Data Ingestion Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE                             │
│                 POST /run-ingestion                               │
└─────────────────────────────────────────────────────────────────┘

    Trigger: User hits POST /run-ingestion
                │
                ▼
    ┌──────────────────────────┐
    │  Step 1: Launch Browser   │
    │  Selenium + ChromeDriver  │
    │  • Stealth user-agent     │
    │  • --disable-blink-       │
    │    features=Automation    │
    │    Controlled             │
    └────────────┬─────────────┘
                 │
                 ▼
    ┌──────────────────────────┐
    │  Step 2: Fetch NSE API    │
    │  Execute async JS in      │
    │  browser to call:         │
    │  nseindia.com/api/        │
    │  equity-stockIndices?     │
    │  index=NIFTY%2050         │
    └────────────┬─────────────┘
                 │
          ┌──────┴──────┐
          │             │
      Success        Blocked
          │             │
          ▼             ▼
    ┌──────────┐  ┌──────────────┐
    │ Parse JSON│  │ Yahoo Finance │
    │ Extract:  │  │ Fallback      │
    │ • SYMBOL  │  │ (yfinance)    │
    │ • LTP     │  │               │
    │ • %CHNG   │  │ TCS.NS,       │
    │ • VOLUME  │  │ INFY.NS, etc. │
    └────┬─────┘  └──────┬────────┘
         │               │
         └───────┬───────┘
                 │
                 ▼
    ┌──────────────────────────────┐
    │  Step 3: Dual Storage         │
    │                               │
    │  ┌─────────────────────────┐  │
    │  │ MongoDB                  │  │
    │  │ save_market_stats()      │  │
    │  │ • Clear old data         │  │
    │  │ • Insert fresh records   │  │
    │  │ • 50 stocks × 7 fields   │  │
    │  └─────────────────────────┘  │
    │                               │
    │  ┌─────────────────────────┐  │
    │  │ ChromaDB                 │  │
    │  │ add_documents()          │  │
    │  │ • Delete old collection  │  │
    │  │ • Create text summaries  │  │
    │  │ • Embed via all-MiniLM   │  │
    │  │ • Persist to disk        │  │
    │  └─────────────────────────┘  │
    └──────────────────────────────┘
                 │
                 ▼
    ┌──────────────────────────────┐
    │  Step 4: Log & Report         │
    │  MongoDB ingestion_logs       │
    │  {status, timestamp}          │
    └──────────────────────────────┘
```

### Anti-Bot Bypass Strategy

NSE uses Cloudflare + bot detection. The scraper counters with:
1. **Selenium** (not plain `requests`) → real browser fingerprint
2. **Real User-Agent** header → mimics Chrome 120
3. **`--disable-blink-features=AutomationControlled`** → hides `navigator.webdriver` flag
4. **JavaScript fetch via `execute_async_script`** → uses browser's authenticated session cookies
5. **Yahoo Finance fallback** → graceful degradation if NSE blocks

---

## 6. Component Interaction Diagram (Sequence)

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  User    │   │ Streamlit│   │ FastAPI  │   │ LangGraph│   │  Tools   │   │  Groq    │
│          │   │ (:8501)  │   │ (:8000)  │   │  Agent   │   │          │   │  (LLM)   │
└────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘
     │              │              │              │              │              │
     │  "TCS price?"│              │              │              │              │
     │─────────────►│              │              │              │              │
     │              │  POST /chat  │              │              │              │
     │              │─────────────►│              │              │              │
     │              │              │ agent.invoke │              │              │
     │              │              │─────────────►│              │              │
     │              │              │              │  LLM: "Use   │              │
     │              │              │              │  search_     │              │
     │              │              │              │  market_     │              │
     │              │              │              │  documents"  │              │
     │              │              │              │──────────────│              │
     │              │              │              │              │              │
     │              │              │              │  search_market_documents()  │
     │              │              │              │─────────────►│              │
     │              │              │              │              │  ChromaDB    │
     │              │              │              │              │  query       │
     │              │              │              │              │──────────────│
     │              │              │              │              │◄─────────────│
     │              │              │              │◄─────────────│  results     │
     │              │              │              │              │              │
     │              │              │              │  LLM synthesizes answer     │
     │              │              │              │─────────────────────────────►│
     │              │              │              │◄─────────────────────────────│
     │              │              │              │              │              │
     │              │              │◄─────────────│  final answer│              │
     │              │◄─────────────│  JSON response              │              │
     │◄─────────────│  "₹2,070"    │              │              │              │
     │              │              │              │              │              │
```

---

## 7. Data Models

### MongoDB Collections

```
┌─────────────────────────────────────────────────────┐
│  market_stats                                        │
├──────────┬────────┬────────┬────────┬───────┬────────┤
│ SYMBOL   │ OPEN   │ HIGH   │ LOW    │ LTP   │ %CHNG  │ VOLUME  │
│ (string) │(float) │(float) │(float) │(float)│(float) │ (int)   │
├──────────┼────────┼────────┼────────┼───────┼────────┼─────────┤
│ TCS      │ 2050.0 │ 2085.0 │ 2045.0 │ 2070.0│ +1.20  │ 2300000 │
│ INFY     │ 1590.0 │ 1620.0 │ 1585.0 │ 1600.0│ -0.50  │ 5100000 │
│ ...      │ ...    │ ...    │ ...    │ ...   │ ...    │ ...     │
└──────────┴────────┴────────┴────────┴───────┴────────┴─────────┘

┌──────────────────────────────────────────┐
│  ingestion_logs                           │
├──────────┬───────────────────────────────┤
│ status   │ timestamp                      │
│ (string) │ (datetime)                     │
├──────────┼───────────────────────────────┤
│ success  │ 2026-07-04T18:19:00           │
└──────────┴───────────────────────────────┘
```

### ChromaDB Documents (Vectorized)

```python
# Each stock becomes a text document that gets embedded:
Document(
    page_content="Stock Update: TCS. Current Price (LTP): 2070.0. 
                  Percentage Change: 1.2%. Volume: 2300000.",
    metadata={"source": "market_live", "type": "stock_price"}
)
# Embedded into 384-dimensional vector via all-MiniLM-L6-v2
```

### API Schema (Pydantic)

```python
# Request
class QueryRequest:
    query: str     # "What is TCS price today?"

# Response
class QueryResponse:
    answer: str    # "TCS is trading at ₹2,070..."
    timestamp: datetime
```

---

## 8. Key Design Decisions & Rationale

| Decision | Choice | Why |
|----------|--------|-----|
| **LLM Provider** | Groq (Llama 3.3 70B) | Free tier, 300+ tokens/sec, good for prototyping |
| **Agent Framework** | LangGraph over plain LangChain | Stateful agent loop, better tool-calling control |
| **Embeddings** | Local `all-MiniLM-L6-v2` | Free, no API costs, 384-dim is efficient for small corpus |
| **Vector DB** | ChromaDB (persistent) | Lightweight, Python-native, no separate server needed |
| **Metadata DB** | MongoDB | Flexible schema for evolving financial data |
| **Scraping** | Selenium over Playwright | Better Cloudflare bypass for NSE's specific protections |
| **Fallback** | Yahoo Finance | Ensures system works even when NSE blocks |
| **Frontend** | Streamlit | Fastest path to interactive chat UI in Python |

---

## 9. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DEPLOYMENT VIEW                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│   ┌─────────────────┐                                        │
│   │  User's Machine  │                                        │
│   │  (Localhost)     │                                        │
│   └────────┬────────┘                                        │
│            │                                                  │
│   ┌────────┴────────┐                                        │
│   │   Terminal 3     │  streamlit run frontend.py             │
│   │   :8501          │                                        │
│   └────────┬────────┘                                        │
│            │                                                  │
│   ┌────────┴────────┐                                        │
│   │   Terminal 1     │  python main.py                        │
│   │   :8000 (FastAPI)│                                        │
│   │                  │                                        │
│   │  ┌────────────┐  │                                        │
│   │  │ /chat       │  │────────► Groq API (cloud)             │
│   │  │ /run-       │  │────────► Selenium → NSE (cloud)       │
│   │  │  ingestion  │  │────────► Yahoo Finance (cloud)        │
│   │  └────────────┘  │                                        │
│   └────────┬────────┘                                        │
│            │                                                  │
│   ┌────────┴────────┐                                        │
│   │   Docker          │  docker run mongo:latest              │
│   │   MongoDB :27017  │                                        │
│   └──────────────────┘                                        │
│                                                               │
│   ┌──────────────────┐                                        │
│   │  Local Disk       │  chroma_db/ (SQLite + embeddings)     │
│   └──────────────────┘                                        │
│                                                               │
│   Required: 3 terminals + Docker                              │
│   External: Groq API, NSE website, Yahoo Finance              │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. Query Routing Logic

```
                     User Query
                         │
                         ▼
              ┌──────────────────────┐
              │   LLM Classifies      │
              │   Intent + Entities   │
              └──────────┬───────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │Qualitative│  │Quantitative│ │Prediction│
    │(RAG)     │  │(Structured)│  │(Heuristic)│
    └────┬─────┘  └────┬─────┘  └────┬─────┘
         │              │              │
         ▼              ▼              ▼
   search_market  get_top_gainers  predict_stock
   _documents()   _losers()        _price()
         │              │              │
         ▼              ▼              ▼
    ChromaDB        MongoDB         Random
    (vector         (sort by        heuristic
     search)         %CHNG)         model
         │              │              │
         └──────────────┼──────────────┘
                        │
                        ▼
              ┌──────────────────────┐
              │  LLM Synthesizes      │
              │  Final Answer         │
              └──────────────────────┘
```

---

## 11. Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **LLM Latency** | ~1-3s | Groq's optimized inference for Llama 3.3 70B |
| **Embedding Time** | ~50ms/doc | `all-MiniLM-L6-v2` on CPU, 384-dim |
| **Vector Search** | <10ms | ChromaDB with ~50-100 documents |
| **Scraping Time** | 5-15s | Selenium browser launch + page load + API fetch |
| **Total Docs per Ingestion** | ~50-55 | 50 stocks + option chain summary |
| **Vector Dimensions** | 384 | all-MiniLM-L6-v2 |

---

## 12. Future Enhancements

```
┌─────────────────────────────────────────────────────────────┐
│                    ROADMAP (Not Implemented)                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🔄 Real-time WebSocket streaming of stock prices             │
│  📊 Historical price charts & technical indicators            │
│  🔐 User authentication & personalized watchlists             │
│  🧠 Actual ML prediction model (LSTM/Transformer)             │
│     replacing the dummy heuristic                             │
│  📰 Real PDF parsing from NSE corporate announcements         │
│  🐳 Full Docker Compose (API + Mongo + Chroma in containers)  │
│  ☁️ Deploy to cloud (AWS EC2 / Vercel / Railway)             │
│  📈 Multi-index support (Bank Nifty, Sensex, etc.)            │
│  🗣️ Voice interface integration                              │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Appendix: Project Structure

```
nifty_rag_bot/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── requirements.txt     # Python dependencies
│   ├── .env                 # API keys & config
│   ├── src/
│   │   ├── agent.py         # LangGraph Agent + tool registration
│   │   ├── scraper.py       # Selenium NSE scraper + yfinance fallback
│   │   ├── database.py      # MongoDB connection & CRUD
│   │   ├── vector_store.py  # ChromaDB setup & embedding logic
│   │   ├── tools.py         # Agent tool definitions (@tool decorators)
│   │   └── models.py        # Pydantic schemas
│   ├── chroma_db/           # Persistent vector store (gitignored)
│   └── test/                # Test scripts
├── frontend.py              # Streamlit chat UI
├── HLD.md                   # This document
└── README.md                # Setup instructions
```
