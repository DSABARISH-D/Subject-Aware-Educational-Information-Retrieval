from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from config import settings
import logging
import os

logger = logging.getLogger(__name__)

Base = declarative_base()

IS_SQLITE = False

try:
    db_url = settings.database_url
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(db_url)
    with engine.connect() as conn:
        pass
    logger.info("Connected to PostgreSQL database.")
except Exception as e:
    logger.warning(f"PostgreSQL connection failed ({e}). Falling back to SQLite database (app_fallback.db).")
    engine = create_engine("sqlite:///./app_fallback.db", connect_args={"check_same_thread": False})
    IS_SQLITE = True

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_sqlite_schema() -> None:
    """Add metadata columns to an older development fallback database without deleting data."""
    if not IS_SQLITE:
        return

    columns = {
        "documents": [
            ("content_hash", "VARCHAR(64)"),
            ("source_type", "VARCHAR(20) NOT NULL DEFAULT 'student'"),
        ],
        "chunks": [
            ("page_number", "INTEGER"),
            ("chunk_index", "INTEGER NOT NULL DEFAULT 0"),
            ("source_type", "VARCHAR(20) NOT NULL DEFAULT 'student'"),
        ],
    }
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table, additions in columns.items():
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, definition in additions:
                if name not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
