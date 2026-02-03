import os
import time
import pandas as pd
import shutil
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from langchain_core.documents import Document
from src.vector_store import add_documents

DOWNLOAD_DIR = os.path.abspath("./data")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def wait_for_download(directory, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(5)


def get_latest_file(directory):
    files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if not f.endswith(".crdownload")
    ]
    return max(files, key=os.path.getctime)


def scrape_nse_data():
    print("Starting NSE CSV download...")

    today = datetime.now().strftime("%Y-%m-%d")
    final_filename = f"financial_data_{today}.csv"

    chrome_options = Options()
    # chrome_options.add_argument("--headless=new")   # turn off if blocked
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--start-maximized")

    # 🔥 Auto-download configuration
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    try:
        driver.get(
            "https://www.nseindia.com/market-data/live-equity-market?symbol=NIFTY%2050"
        )

        # Allow Cloudflare + JS to initialize
        time.sleep(10)

        # ✅ Wait for EXACT download button by ID
        download_btn = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "dnldEquityStock"))
        )

        # NSE binds click via JS → force JS click
        driver.execute_script("arguments[0].click();", download_btn)

        print("Download button clicked")

        # ⏳ Wait for download completion
        wait_for_download(DOWNLOAD_DIR)

        # 🔄 Rename file
        downloaded_file = get_latest_file(DOWNLOAD_DIR)
    
        final_path = os.path.join(DOWNLOAD_DIR, final_filename)

        shutil.move(downloaded_file, final_path)

        print(f"SUCCESS: File saved as {final_path}")

    except Exception as e:
        print(f"ERROR: {e}")

    finally:
        driver.quit()
    
    records=pd.csv(final_path)

    if records:
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
