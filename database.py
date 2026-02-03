import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import JSONB

# 1. DATABASE CONFIGURATION
# Fetch DATABASE_URL from .env or Render environment
DATABASE_URL = os.environ.get("DATABASE_URL")

# Fallback for local testing if no DB url is provided (SQLite)
if not DATABASE_URL:
    print("⚠️ WARNING: DATABASE_URL not set. Using local SQLite (cache.db) for testing.")
    DATABASE_URL = "sqlite:///./cache.db"
elif DATABASE_URL.startswith("postgres://"):
    # SQLAlchemy requires 'postgresql://', Render sometimes gives 'postgres://'
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. MODEL DEFINITION
class AnalysisCache(Base):
    """
    SQLAlchemy model for storing Scraper & NLP results.
    Acts as a persistent cache.
    """
    __tablename__ = "analysis_cache"

    id = Column(Integer, primary_key=True, index=True)
    url_hash = Column(String, unique=True, index=True, nullable=False)
    maps_url = Column(Text, nullable=False)
    business_name = Column(Text, nullable=True)
    
    # Store the full result JSON (sentiment, ratings, reviews list)
    # Use JSONB for Postgres for efficiency, JSON for SQLite compatibility
    analysis_json = Column(JSON) 
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# 3. HELPER FUNCTIONS
def init_db():
    """Creates tables if they don't exist."""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables initialized.")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")

def get_db():
    """Dependency generator for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. CACHE LOGIC
def get_cached_analysis(db, url_hash: str):
    """Retrieve analysis from DB by hash."""
    return db.query(AnalysisCache).filter(AnalysisCache.url_hash == url_hash).first()

def save_analysis(db, url_hash: str, maps_url: str, business_name: str, analysis_data: dict):
    """Saves or updates the analysis result."""
    existing = get_cached_analysis(db, url_hash)
    
    if existing:
        print(f"🔄 Updating cache for {business_name}...")
        existing.analysis_json = analysis_data
        existing.business_name = business_name
        existing.updated_at = datetime.datetime.utcnow()
    else:
        print(f"💾 Creating new cache entry for {business_name}...")
        new_entry = AnalysisCache(
            url_hash=url_hash,
            maps_url=maps_url,
            business_name=business_name,
            analysis_json=analysis_data
        )
        db.add(new_entry)
    
    try:
        db.commit()
        if existing:
            db.refresh(existing)
    except Exception as e:
        db.rollback()
        print(f"❌ Error saving to DB: {e}")
