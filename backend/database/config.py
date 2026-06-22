"""
Database configuration for TENeT project
Using SQLite for local development (can be upgraded to PostgreSQL later)
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
# Use SQLite for now - stored in backend/data/tenet.db
DB_TYPE = os.getenv('DB_TYPE', 'sqlite')

if DB_TYPE == 'sqlite':
    # SQLite database path
    DB_PATH = os.getenv('DB_PATH', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'tenet.db'))
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    
    # Create engine for SQLite
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # Required for SQLite
        echo=False  # Set to True for SQL query logging
    )
else:
    # PostgreSQL configuration (for future use)
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'tenet_db')
    
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Create engine for PostgreSQL
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def init_db():
    """
    Initialize database tables
    """
    # Import models to register them with Base
    from database.models import CATRegion, CATDataPoint, CATUpload, CATGatingRule
    
    Base.metadata.create_all(bind=engine)
    
    if DB_TYPE == 'sqlite':
        print(f"✓ SQLite database initialized at: {DB_PATH}")
    else:
        print(f"✓ PostgreSQL database initialized at: {DB_HOST}:{DB_PORT}/{DB_NAME}")
