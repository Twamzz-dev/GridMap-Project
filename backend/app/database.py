from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Initialize Base class for declarative models
Base = declarative_base()

# Database URL Configuration
SQLALCHEMY_DATABASE_URL = "sqlite:////home/bankai/Desktop/grid/gm/GridMap-Project/backend/test.db"  # SQLite database file with absolute path

# Create engine instance
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Create sessionmaker
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Export these for use in other modules
__all__ = ['Base', 'SessionLocal', 'engine']

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()