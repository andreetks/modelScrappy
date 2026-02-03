from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import hashlib
import os

app = FastAPI(title="Google Maps Sentiment API")

_nlp_engine = None

def get_nlp_engine():
    global _nlp_engine
    if _nlp_engine is None:
        from nlp import ReviewAnalyzer
        _nlp_engine = ReviewAnalyzer()
    return _nlp_engine

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.on_event("startup")
def startup_event():
    try:
        import database
        database.init_db()
    except Exception as e:
        print(f"Startup Warning: {e}")

class AnalysisRequest(BaseModel):
    maps_url: str
    forceUpdate: bool = False
    limit: int = 50

@app.post("/analyze")
def analyze_reviews(req: AnalysisRequest):
    import database
    from scraper import GoogleMapsScraper
    
    db = database.SessionLocal()
    
    try:
        url_hash = hashlib.md5(req.maps_url.encode()).hexdigest()

        # 1. Intentar Cache
        if not req.forceUpdate:
            cached_entry = database.get_cached_analysis(db, url_hash)
            if cached_entry:
                print(f"✅ Serving from Cache: {url_hash}")
                return {**cached_entry.analysis_json, "cached": True}

        # 2. Intentar Scrape
        print(f"🚀 Scraping: {req.maps_url}")
        scraper = GoogleMapsScraper(url=req.maps_url, max_reviews=req.limit, headless=True)
        raw_reviews = scraper.scrape(return_data=True)

        # # 3. FALLBACK: Si no hay reseñas, loguear error y buscar cualquier registro en DB
        # if not raw_reviews:
        #     print(f"❌ ERROR: No se encontraron reseñas nuevas para {req.maps_url}")
            
        #     # Intentamos recuperar lo que sea que tengamos en la DB (aunque sea viejo)
        #     fallback_entry = database.get_cached_analysis(db, url_hash)
        #     if fallback_entry:
        #         print(f"📦 Fallback: Devolviendo última coincidencia de '{fallback_entry.business_name}'")
        #         return {**fallback_entry.analysis_json, "cached": True, "fallback": True}
        #     else:
        #         raise HTTPException(status_code=404, detail="No se encontraron reseñas y no hay datos en la base de datos.")
        # 3. FALLBACK: Si no hay reseñas, buscar en cache o un registro aleatorio
        if not raw_reviews:
            print(f"❌ ERROR: No se encontraron reseñas nuevas para {req.maps_url}")
            
            # A. Intentamos recuperar la última versión de ESA URL específica
            fallback_entry = database.get_cached_analysis(db, url_hash)
            
            if fallback_entry:
                print(f"📦 Fallback: Devolviendo última coincidencia de '{fallback_entry.business_name}'")
                return {**fallback_entry.analysis_json, "cached": True, "fallback": True}
            
            # B. Si ni siquiera esa URL existe, traemos CUALQUIER registro al azar (Nuevo paso)
            from sqlalchemy.sql.expression import func
            # Asumiendo que tu modelo en database.py se llama Analysis
            random_entry = db.query(database.Analysis).order_by(func.random()).first()
            
            if random_entry:
                print(f"🎲 Azar: Devolviendo registro aleatorio de '{random_entry.business_name}'")
                return {**random_entry.analysis_json, "cached": True, "fallback_random": True}
            else:
                raise HTTPException(status_code=404, detail="La base de datos está vacía y no hay reseñas nuevas.")


        # 4. Procesar NLP
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

        # 5. Guardar
        database.save_analysis(db, url_hash, req.maps_url, business_name, final_response)
        return final_response

    except Exception as e:
        print(f"❌ Error en el servidor: {str(e)}")
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()