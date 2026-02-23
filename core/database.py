import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv(override=False)  # Don't override existing container env vars

POSTGRES_USER = os.getenv("POSTGRES_USER", "scraper_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "scraper_pass")
POSTGRES_DB = os.getenv("POSTGRES_DB", "scraper_db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# Constructing the connection string
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# create_engine establishes the database connection
engine = create_engine(DATABASE_URL, echo=False)

# SessionLocal is the factory for new Session objects
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our models
Base = declarative_base()

def get_db():
    """Dependency to get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
