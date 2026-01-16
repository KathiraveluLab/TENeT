"""
Database configuration and ORM models for TENeT.

Uses SQLAlchemy with SQLite for development, easily upgradeable to PostgreSQL.
Designed to work seamlessly with FastAPI's dependency injection.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Generator
import os

# Database URL - SQLite for development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tenet.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class Community(Base):
    """
    Community record with healthcare, connectivity, and access data.
    
    This is the primary entity representing Alaska communities.
    """
    __tablename__ = "communities"

    id = Column(Integer, primary_key=True, index=True)
    community_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    region = Column(String(255), nullable=True)
    
    # Geographic data
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Demographics
    population = Column(Integer, nullable=True)
    
    # Tier classification (1=best access, 3=most isolated)
    access_tier = Column(Integer, nullable=True)
    
    # Season-specific access scores (0-100)
    summer_access_score = Column(Float, nullable=True)
    winter_access_score = Column(Float, nullable=True)
    
    # Healthcare data (stored as JSON for flexibility)
    healthcare_data = Column(JSON, nullable=True)
    
    # Connectivity data (stored as JSON)
    connectivity_data = Column(JSON, nullable=True)
    
    # Access/transport data (stored as JSON)
    access_data = Column(JSON, nullable=True)
    
    # Data quality metrics
    data_completeness = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Community {self.name} (Tier {self.access_tier})>"


class HealthcareFacility(Base):
    """
    Individual healthcare facilities (hospitals, clinics, pharmacies).
    """
    __tablename__ = "healthcare_facilities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    facility_type = Column(String(100), nullable=False)  # hospital, clinic, pharmacy
    
    # Location
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Associated community (if applicable)
    community_id = Column(String(50), nullable=True, index=True)
    
    # Services
    has_emergency = Column(Boolean, default=False)
    specialties = Column(JSON, nullable=True)  # List of medical specialties
    
    # Data source
    source = Column(String(100), nullable=True)  # e.g., "OSM", "Healthsites"
    confidence = Column(String(20), nullable=True)  # high, medium, low
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<HealthcareFacility {self.name} ({self.facility_type})>"


class BroadbandCoverage(Base):
    """
    Broadband coverage data for communities.
    """
    __tablename__ = "broadband_coverage"
    
    id = Column(Integer, primary_key=True, index=True)
    community_id = Column(String(50), index=True, nullable=False)
    
    # Coverage metrics
    coverage_percent = Column(Float, nullable=True)  # Percentage of area covered
    download_mbps = Column(Float, nullable=True)
    upload_mbps = Column(Float, nullable=True)
    latency_ms = Column(Float, nullable=True)
    
    # Technology type
    primary_technology = Column(String(100), nullable=True)  # fiber, cable, satellite, etc.
    
    # Provider info
    provider_count = Column(Integer, nullable=True)
    
    # Data quality
    source = Column(String(100), nullable=True)  # e.g., "FCC", "Ookla"
    confidence = Column(String(20), nullable=True)
    data_gaps = Column(Text, nullable=True)  # Description of known gaps
    
    # Timestamps
    collected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<BroadbandCoverage {self.community_id}: {self.download_mbps}Mbps>"


# Database initialization
def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)


# Dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.
    
    Usage:
        @app.get("/communities")
        def list_communities(db: Session = Depends(get_db)):
            return db.query(Community).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
