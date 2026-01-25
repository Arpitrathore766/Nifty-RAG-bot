import os
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from src.database import save_market_stats, log_ingestion
from src.vector_store import add_documents
from langchain_core.documents import Document
import yfinance as yf # Fallback library

DATA_DIR = "./data"
os.makedirs(DATA_DIR, exist_ok=True)

async def scrape_nse_data():
    """Main pipeline function with Fallback."""
    print("Starting Ingestion Pipeline...")
    records = []
    
    # --- ATTEMPT 1: SCRAPING NSE (With HTTP/1.1 Forced) ---
    print("Attempting to scrape NSE directly (HTTP/1.1)...")
    try:
        async with async_playwright() as p:
            # Force HTTP/1.1 to bypass HTTP2 Protocol Errors
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-http2',              # <--- THE KEY FIX
                    '--ignore-certificate-errors', 
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
            )
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()
            
            # Go directly to table page
            await page.goto("https://www.nseindia.com/market-data/live-equity-market?symbol=NIFTY%2050", timeout=30000)
            await page.wait_for_selector("table", timeout=10000)
            
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find table
            tables = soup.find_all('table')
            if tables:
                df = pd.read_html(str(tables[0]))[0]
                # Cleanup Data
                required_cols = ['SYMBOL', 'OPEN', 'HIGH', 'LOW', 'LTP', '%CHNG', 'VOLUME']
                # Basic rename if columns don't match exactly
                if 'Symbol' in df.columns: df.rename(columns={'Symbol': 'SYMBOL'}, inplace=True)
                if 'Last Price' in df.columns: df.rename(columns={'Last Price': 'LTP'}, inplace=True)
                if '% Change' in df.columns: df.rename(columns={'% Change': '%CHNG'}, inplace=True)
                
                records = df.to_dict('records')
                print(f"SUCCESS: Scraped {len(records)} stocks from NSE Website.")
            
            await browser.close()
            
    except Exception as e:
        print(f"Warning: Direct scraping failed ({e}). Switching to Backup Source...")

    # --- ATTEMPT 2: BACKUP (YFINANCE) ---
    # If scraping failed, use this to ensure the database gets populated
    if not records:
        print("Fetching data from Backup Source (Yahoo Finance)...")
        try:
            # Nifty 50 Tickers (Top 5 for demo speed, or full list)
            tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS"]
            data = yf.download(tickers, period="1d", progress=False)
            
            # Format into our standard structure
            for ticker in tickers:
                try:
                    # Handle multi-index columns from yfinance
                    current_price = data['Close'][ticker].iloc[-1]
                    open_price = data['Open'][ticker].iloc[-1]
                    vol = data['Volume'][ticker].iloc[-1]
                    
                    # Calculate dummy change if previous close is missing
                    change = round(((current_price - open_price) / open_price) * 100, 2)
                    
                    records.append({
                        "SYMBOL": ticker.replace(".NS", ""),
                        "LTP": round(current_price, 2),
                        "%CHNG": change,
                        "VOLUME": int(vol),
                        "OPEN": round(open_price, 2),
                        "HIGH": round(data['High'][ticker].iloc[-1], 2),
                        "LOW": round(data['Low'][ticker].iloc[-1], 2)
                    })
                except Exception:
                    continue
            print(f"SUCCESS: Retrieved {len(records)} stocks from Backup.")
            
        except Exception as e:
            print(f"Critical Error: Backup source also failed: {e}")

    # --- SAVE TO DB ---
    if records:
        # 1. Save Structured Data for "Top Gainers" math
        save_market_stats(records)
        
        # 2. Save Semantic Data for RAG
        docs = []
        for r in records:
            content = f"Stock: {r.get('SYMBOL')}. Price: {r.get('LTP')}. Change: {r.get('%CHNG')}%. Volume: {r.get('VOLUME')}."
            docs.append(Document(page_content=content, metadata={"source": "market_live", "type": "structured"}))
        
        add_documents(docs)
    else:
        print("No data collected.")

    # --- PDF SIMULATION ---
    print("Checking for PDF announcements...")
    dummy_pdf_path = os.path.join(DATA_DIR, "reliance_announcement.pdf")
    if not os.path.exists(dummy_pdf_path):
         with open(dummy_pdf_path.replace(".pdf", ".txt"), "w") as f:
            f.write("RELIANCE INDUSTRIES: Board meeting scheduled for Dividend on 2026-01-22.")
    
    with open(dummy_pdf_path.replace(".pdf", ".txt"), "r") as f:
        text = f.read()
    add_documents([Document(page_content=text, metadata={"source": "RELIANCE", "type": "pdf"})])

    log_ingestion({"status": "success", "timestamp": datetime.now()})
    print("Pipeline Complete.")
# import os
# import pandas as pd
# from datetime import datetime
# from bs4 import BeautifulSoup
# from playwright.async_api import async_playwright  # <--- CHANGED to Async
# from src.database import save_market_stats, log_ingestion
# from src.vector_store import add_documents
# from langchain_core.documents import Document
# import fitz  # PyMuPDF

# DATA_DIR = "./data"
# os.makedirs(DATA_DIR, exist_ok=True)

# async def scrape_nse_data():  # <--- CHANGED to async def
#     """Main pipeline function."""
#     print("Starting Ingestion Pipeline...")
    
#     async with async_playwright() as p:  # <--- CHANGED to async with
#         # Launch browser (headless=True for server)
#         browser = await p.chromium.launch(headless=True) # <--- AWAIT
#         page = await browser.new_page() # <--- AWAIT
        
#         # 1. Scrape Nifty 50 Stats (Gainers/Losers)
#         print("Scraping Nifty 50 stats...")
#         try:
#             await page.goto("https://www.nseindia.com/market-data/live-equity-market?symbol=NIFTY%2050", timeout=60000) # <--- AWAIT
#             await page.wait_for_selector("table", timeout=10000) # <--- AWAIT
            
#             # Extract table content
#             html = await page.content() # <--- AWAIT
#             soup = BeautifulSoup(html, 'html.parser')
#             table = soup.find('table', {'id': 'equityStockTable'}) 
            
#             # Fallback parsing
#             if not table:
#                 table = soup.find_all('table')[0]
                
#             df = pd.read_html(str(table))[0]
            
#             # Clean Data
#             df = df[['SYMBOL', 'OPEN', 'HIGH', 'LOW', 'LTP', '%CHNG', 'VOLUME']]
#             records = df.to_dict('records')
            
#             # Store in MongoDB
#             save_market_stats(records)
            
#             # Create Text Summaries for Vector DB
#             docs = []
#             for r in records:
#                 content = f"Stock: {r['SYMBOL']}. Price: {r['LTP']}. Change: {r['%CHNG']}%. Volume: {r['VOLUME']}."
#                 docs.append(Document(page_content=content, metadata={"source": "nifty_live", "type": "structured"}))
#             add_documents(docs)
#             print(f"Scraped and stored {len(records)} stock records.")
            
#         except Exception as e:
#             print(f"Error scraping table: {e}")

#         # 2. Scrape Corporate Announcements (PDFs)
#         print("Checking for PDF announcements...")
#         try:
#             dummy_pdf_path = os.path.join(DATA_DIR, "reliance_announcement.pdf")
#             if not os.path.exists(dummy_pdf_path):
#                 with open(dummy_pdf_path.replace(".pdf", ".txt"), "w") as f:
#                     f.write("RELIANCE INDUSTRIES: Board meeting scheduled for Dividend on 2026-01-22.")
            
#             with open(dummy_pdf_path.replace(".pdf", ".txt"), "r") as f:
#                 text = f.read()
                
#             docs = [Document(page_content=text, metadata={"source": "RELIANCE", "type": "pdf", "date": str(datetime.now().date())})]
#             add_documents(docs)
            
#         except Exception as e:
#             print(f"Error processing PDFs: {e}")
            
#         await browser.close() # <--- AWAIT

#     log_ingestion({"status": "success", "timestamp": datetime.now()})
#     print("Pipeline Complete.")
