from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import sys

# Add current directory to path so we can import scraper
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stream_scraper.scraper import scrape_stream_app_mode

app = FastAPI()

class ScrapeRequest(BaseModel):
    url: str

@app.get("/")
def home():
    return {"status": "running", "message": "FaselHD Scraper API is active."}

@app.get("/scrape")
def scrape_endpoint(url: str):
    print(f"Received scrape request for: {url}")
    result = scrape_stream_app_mode(url)
    
    if result and "error" in result:
        # If scraper reported an error, we return it but with 200 OK so frontend can display it
        # Or we could return 500, but handling JSON with specific error msg is easier in frontend
        return result
    
    if not result:
        return {"error": "Scraper returned no data."}
        
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
