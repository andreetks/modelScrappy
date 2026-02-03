from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import hashlib
import os

# --- LIGHTWEIGHT API DEFINITION ---
# No heavy imports here (no transformers, no playwright, no database)

app = FastAPI(title="Google Maps Sentiment API (Optimized for Render)")

# Global cache for NLP model to avoid reloading on every request
_nlp_engine = None

def get_nlp_engine():
    global _nlp_engine
    if _nlp_engine is None:
        print("Lazy Loading NLP Engine...")
        from nlp import ReviewAnalyzer
        _nlp_engine = ReviewAnalyzer()
    return _nlp_engine

@app.get("/")
def health_check():
    """
    Simple health check that runs immediately without loading heavy libs.
    Allows Render to detect the open port fast.
    """
    return {"status": "ok", "service": "Google Maps NLP API", "ready": True}

@app.on_event("startup")
def startup_event():
    """
    Initialize Database tables on startup.
    This runs AFTER the app is created, allowing Uvicorn to bind the socket.
    """
    try:
        print("Startup: Initializing Database...")
        import database
        database.init_db()
        print("Startup: Database initialized.")
    except Exception as e:
        print(f"Startup Warning: Database init failed (might be connection issue): {e}")

class AnalysisRequest(BaseModel):
    maps_url: str
    forceUpdate: bool = False
    limit: int = 50

# @app.post("/analyze")
# def analyze_reviews(req: AnalysisRequest):
    """
    Main endpoint using Lazy Imports.
    """
    # 1. LAZY IMPORTS
    import database
    from scraper import GoogleMapsScraper
    
    # Manual DB Session Management
    # standard SQLAlchemy pattern: create session, try, finally close
    db = database.SessionLocal()
    
    try:
        # Calculate Hash
        url_hash = hashlib.md5(req.maps_url.encode()).hexdigest()

        # 2. Check Cache
        if not req.forceUpdate:
            cached_entry = database.get_cached_analysis(db, url_hash)
            if cached_entry:
                print(f"✅ Serving from PostgreSQL Cache (Hash: {url_hash})")
                return {**cached_entry.analysis_json, "cached": True}

        # 3. Scrape
        print(f"🚀 Scraping Fresh Data for: {req.maps_url}")
        scraper = GoogleMapsScraper(url=req.maps_url, max_reviews=req.limit, headless=True)
        raw_reviews = scraper.scrape(return_data=True)

        if not raw_reviews:
            raise HTTPException(status_code=404, detail="No reviews found or scraping failed.")

        # 4. NLP Analysis
        print("🧠 Running NLP Analysis...")
        nlp = get_nlp_engine()
        analysis_result = nlp.analyze(raw_reviews)
        
        business_name = raw_reviews[0].get("business_name") if raw_reviews else "Unknown"

        final_response = {
            "business_name": business_name,
            "total_reviews": analysis_result["total_reviews"],
            "sentiment_summary": analysis_result["sentiment_summary"],
            "average_rating": analysis_result["average_rating"],
            "reviews": analysis_result["reviews"],
            "cached": False
        }

        # 5. Save to Cache
        database.save_analysis(
            db, 
            url_hash=url_hash, 
            maps_url=req.maps_url, 
            business_name=business_name, 
            analysis_data=final_response
        )

        return final_response

    except Exception as e:
        print(f"❌ Error in /analyze: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/analyze")
def analyze_reviews(req: AnalysisRequest):
    import database
    from scraper import GoogleMapsScraper
    import hashlib
    
    db = database.SessionLocal()
    
    try:
        url_hash = hashlib.md5(req.maps_url.encode()).hexdigest()

        # 1. Intentar usar Cache si no se fuerza la actualización
        if not req.forceUpdate:
            cached_entry = database.get_cached_analysis(db, url_hash)
            if cached_entry:
                print(f"✅ Serving from PostgreSQL Cache (Hash: {url_hash})")
                return {**cached_entry.analysis_json, "cached": True}

        # 2. Intentar Scrapear nuevos datos
        print(f"🚀 Scraping Fresh Data for: {req.maps_url}")
        scraper = GoogleMapsScraper(url=req.maps_url, max_reviews=req.limit, headless=True)
        raw_reviews = scraper.scrape(return_data=True)

        # 3. Lógica de Fallback con Log de Error
        if not raw_reviews:
            # ESTE ES EL LOG QUE SOLICITASTE
            print(f"❌ ERROR: No se encontraron reseñas en la web para la URL: {req.maps_url}")
            
            fallback_entry = database.get_cached_analysis(db, url_hash)
            if fallback_entry:
                print(f"📦 INFO: Usando última coincidencia encontrada en DB para: {fallback_entry.business_name}")
                return {**fallback_entry.analysis_json, "cached": True, "fallback_mode": True}
            else:
                print(f"⚠️ ERROR CRÍTICO: No hay datos previos en DB para esta URL.")
                raise HTTPException(status_code=404, detail="No se encontraron reseñas y no hay respaldo en la base de datos.")

        # 4. Si hay reseñas, procesar con NLP
        print("🧠 Running NLP Analysis...")
        nlp = get_nlp_engine()
        analysis_result = nlp.analyze(raw_reviews)
        
        business_name = raw_reviews[0].get("business_name") if raw_reviews else "Unknown"

        # Asegúrate de que este diccionario esté bien cerrado
        final_response = {
            "business_name": business_name,
            "total_reviews": analysis_result["total_reviews"],
            "sentiment_summary": analysis_result["sentiment_summary"],
            "average_rating": analysis_result["average_rating"],
            "reviews": analysis_result["reviews"],
            "cached": False
        }

        # 5. Guardar en DB para futuros fallbacks
        database.save_analysis(
            db, 
            url_hash=url_hash, 
            maps_url=req.maps_url, 
            business_name=business_name, 
            analysis_data=final_response
        )

        return final_response

    except Exception as e:
        print(f"❌ Error en el servidor: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# Re-implementing manual session logic inside the endpoint to be robust
