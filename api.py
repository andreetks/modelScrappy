from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import hashlib
import os

# Modules
from scraper import GoogleMapsScraper
from nlp import ReviewAnalyzer
import database # PostgreSQL Cache Module

app = FastAPI(title="Google Maps Sentiment API (PostgreSQL)")

# Initialize NLP Model (Global)
nlp_engine = None

@app.on_event("startup")
def startup_event():
    # 1. Initialize DB Tables
    database.init_db()
    
    # 2. Load NLP Model
    global nlp_engine
    if not os.environ.get("SKIP_NLP_LOAD"):
        nlp_engine = ReviewAnalyzer()

class AnalysisRequest(BaseModel):
    maps_url: str
    forceUpdate: bool = False
    limit: int = 50

@app.post("/analyze")
def analyze_reviews(req: AnalysisRequest, db: Session = Depends(database.get_db)):
    """
    Main endpoint:
    1. Check Postgres Cache
    2. If miss or forceUpdate -> Scrape -> NLP -> Save to DB
    3. Return Data
    """
    global nlp_engine
    if nlp_engine is None: nlp_engine = ReviewAnalyzer()

    # Calculate Hash
    url_hash = hashlib.md5(req.maps_url.encode()).hexdigest()

    # 1. Check Cache (PostgreSQL)
    if not req.forceUpdate:
        cached_entry = database.get_cached_analysis(db, url_hash)
        if cached_entry:
            print(f"✅ Serving from PostgreSQL Cache (Hash: {url_hash})")
            return {**cached_entry.analysis_json, "cached": True}

    # 2. Scrape
    print(f"🚀 Scraping Fresh Data for: {req.maps_url}")
    scraper = GoogleMapsScraper(url=req.maps_url, max_reviews=req.limit, headless=True)
    raw_reviews = scraper.scrape(return_data=True)

    if not raw_reviews:
        raise HTTPException(status_code=404, detail="No reviews found or scraping failed.")

    # 3. NLP Analysis
    print("🧠 Running NLP Analysis...")
    analysis_result = nlp_engine.analyze(raw_reviews)
    
    # Extract Business Name safely
    business_name = raw_reviews[0].get("business_name") if raw_reviews else "Unknown"

    final_response = {
        "business_name": business_name,
        "total_reviews": analysis_result["total_reviews"],
        "sentiment_summary": analysis_result["sentiment_summary"],
        "average_rating": analysis_result["average_rating"],
        "reviews": analysis_result["reviews"],
        "cached": False
    }

    # 4. Save to Cache (PostgreSQL)
    database.save_analysis(
        db, 
        url_hash=url_hash, 
        maps_url=req.maps_url, 
        business_name=business_name, 
        analysis_data=final_response
    )

    return final_response

@app.get("/")
def health_check():
    return {"status": "ok", "service": "Google Maps NLP API"}
