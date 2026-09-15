from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from config import settings
import logging
import os

logger = logging.getLogger(__name__)

Base = declarative_base()

IS_SQLITE = False

try:
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        pass
    logger.info("Connected to PostgreSQL database.")
except Exception as e:
    if settings.allow_sqlite_fallback or os.getenv("DATABASE_URL", "").startswith("sqlite"):
        logger.warning(f"PostgreSQL connection failed ({e}). Falling back to SQLite database (app_fallback.db).")
        engine = create_engine("sqlite:///./app_fallback.db", connect_args={"check_same_thread": False})
        IS_SQLITE = True
    else:
        raise RuntimeError(
            "PostgreSQL is unavailable and SQLite fallback is disabled. "
            "Start PostgreSQL or set ALLOW_SQLITE_FALLBACK=true for development."
        ) from e

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
