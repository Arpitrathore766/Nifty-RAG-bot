import os
import time
import json
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from src.database import save_market_stats, log_ingestion
from src.vector_store import add_documents
from langchain_core.documents import Document
import yfinance as yf  # Fallback

# --- CONFIGURATION ---
DATA_DIR = "./data"
os.makedirs(DATA_DIR, exist_ok=True)

def get_driver():
    """Initializes a Stealth Chrome Driver to bypass NSE Bot Detection."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    # Real User-Agent is CRITICAL for NSE
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def fetch_nse_api_data(driver, api_url, referer_url):
    """
    Fetches JSON data from NSE's internal APIs using Selenium's valid cookies.
    This mimics clicking the 'Download' button.
    """
    try:
        # 1. Load the page first to establish the Session/Cookies
        print(f"Connecting to NSE Session via {referer_url}...")
        driver.get(referer_url)
        time.sleep(3) # Wait for cookies to set

        # 2. Use JavaScript to fetch the data using the browser's valid session
        # This bypasses the headers check that blocks standard Python 'requests'
        script = f"""
            var callback = arguments[arguments.length - 1];
            fetch('{api_url}', {{ 
                headers: {{ 'X-Requested-With': 'XMLHttpRequest' }} 
            }})
            .then(response => response.json())
            .then(data => callback(data))
            .catch(err => callback(null));
        """
        print(f"Fetching API: {api_url}")
        data = driver.execute_async_script(script)
        return data
    except Exception as e:
        print(f"API Fetch Error: {e}")
        return None

def process_market_stats(driver):
    """Scrapes Nifty 50 Stock Prices (Infosys, Reliance, etc.)"""
    # The API endpoint for the Nifty 50 Table
    api_url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
    referer = "https://www.nseindia.com/market-data/live-equity-market?symbol=NIFTY%2050"
    
    data = fetch_nse_api_data(driver, api_url, referer)
    records = []
    
    if data and 'data' in data:
        print(f"SUCCESS: Fetched valid JSON data from NSE.")
        # NSE JSON structure: {'data': [{'symbol': 'INFY', 'lastPrice': 1600...}, ...]}
        for item in data['data']:
            try:
                # Normalizing the keys
                records.append({
                    "SYMBOL": item.get('symbol'),
                    "OPEN": item.get('open'),
                    "HIGH": item.get('dayHigh'),
                    "LOW": item.get('dayLow'),
                    "LTP": item.get('lastPrice'),
                    "%CHNG": item.get('pChange'),
                    "VOLUME": item.get('totalTradedVolume')
                })
            except:
                continue
    return records

def process_option_chain(driver):
    """Scrapes Option Chain Data (Just the summary for RAG context)."""
    api_url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    referer = "https://www.nseindia.com/option-chain"
    
    data = fetch_nse_api_data(driver, api_url, referer)
    summary_text = ""
    
    if data and 'records' in data:
        # Just grab the timestamp and underlying value for context
        timestamp = data['records'].get('timestamp')
        nifty_val = data['records'].get('underlyingValue')
        summary_text = f"Nifty 50 Option Chain Status ({timestamp}): Underlying Index Value is {nifty_val}. "
        
        # Grab a few ATM strikes (simple heuristic: middle of the data array)
        if 'data' in data['records']:
            chain = data['records']['data']
            mid_point = len(chain) // 2
            # Take 5 rows from the middle
            for i in range(mid_point - 2, mid_point + 3):
                row = chain[i]
                strike = row.get('strikePrice')
                ce_ltp = row.get('CE', {}).get('lastPrice', 0)
                pe_ltp = row.get('PE', {}).get('lastPrice', 0)
                summary_text += f"[Strike: {strike}, Call Price: {ce_ltp}, Put Price: {pe_ltp}] "
    
    return summary_text

def fetch_fallback_data():
    """Uses Yahoo Finance if NSE blocks us."""
    print("⚠️ NSE Scrape failed. Switching to Yahoo Finance Fallback...")
    tickers = ["INFY.NS", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS"]
    records = []
    try:
        data = yf.download(tickers, period="1d", progress=False)
        # Process multi-index dataframe
        for ticker in tickers:
            sym = ticker.replace('.NS', '')
            try:
                # Robust extraction for different yfinance versions
                ltp = data['Close'][ticker].iloc[-1]
                open_val = data['Open'][ticker].iloc[-1]
                vol = data['Volume'][ticker].iloc[-1]
                pct_chng = ((ltp - open_val) / open_val) * 100
                
                records.append({
                    "SYMBOL": sym,
                    "LTP": round(float(ltp), 2),
                    "OPEN": round(float(open_val), 2),
                    "%CHNG": round(float(pct_chng), 2),
                    "VOLUME": int(vol)
                })
            except:
                continue
        print(f"SUCCESS: Retrieved {len(records)} stocks from Yahoo Finance.")
    except Exception as e:
        print(f"Fallback Error: {e}")
    return records

async def scrape_nse_data():
    """Main Orchestrator."""
    print("Starting Ingestion Pipeline...")
    driver = get_driver()
    all_docs = []
    market_records = []
    
    try:
        # --- 1. MARKET STATS (The Priority) ---
        print("Attempting to fetch Market Stats...")
        market_records = process_market_stats(driver)
        
        # If NSE failed (empty list), trigger Fallback
        if not market_records:
            market_records = fetch_fallback_data()
            
        # --- 2. OPTION CHAIN ---
        # (Optional: Only if NSE didn't block us on the first call)
        if market_records: 
            oc_text = process_option_chain(driver)
            if oc_text:
                all_docs.append(Document(page_content=oc_text, metadata={"source": "NSE", "type": "Option Chain"}))

        # --- 3. SAVE DATA ---
        if market_records:
            # A. Save for "Top Gainers" Tools (MongoDB)
            save_market_stats(market_records)
            
            # B. Save for Chatbot Questions "Price of Infosys" (Vector DB)
            for r in market_records:
                # We create a clear sentence so the LLM can read it easily
                text = f"Stock Update: {r['SYMBOL']}. Current Price (LTP): {r['LTP']}. Percentage Change: {r['%CHNG']}%. Volume: {r['VOLUME']}."
                all_docs.append(Document(page_content=text, metadata={"source": "market_live", "type": "stock_price"}))
            
            # Add to ChromaDB
            add_documents(all_docs)
            print(f"✅ Pipeline Success: Ingested {len(all_docs)} documents.")
        else:
            print("❌ Pipeline Failed: No data collected from Primary or Backup sources.")
            
        log_ingestion({"status": "success" if market_records else "failed", "timestamp": datetime.now()})
        
    except Exception as e:
        print(f"Critical Error: {e}")
    finally:
        driver.quit()