"""
Database models for Community Access Tier (CAT) data
SQLite compatible (can be upgraded to PostgreSQL with PostGIS later)
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.config import Base

class CATRegion(Base):
    """
    Community Access Tier regions with geospatial boundaries
    """
    __tablename__ = 'cat_regions'
    
    id = Column(Integer, primary_key=True, index=True)
    region_name = Column(String(255), nullable=False, index=True)
    region_code = Column(String(50), unique=True, nullable=False)
    tier_level = Column(Integer, nullable=False, index=True)  # 1, 2, 3 for different tiers
    
    # Geospatial data stored as GeoJSON text (for SQLite compatibility)
    # When using PostgreSQL, this can be converted to PostGIS Geometry
    geometry = Column(Text, nullable=True)  # Store as GeoJSON string
    
    # Metadata
    population = Column(Integer, nullable=True)
    area_sqkm = Column(Float, nullable=True)
    access_score = Column(Float, nullable=True)
    
    # Additional properties stored as JSON
    properties = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    data_points = relationship('CATDataPoint', back_populates='region')
    
    def __repr__(self):
        return f"<CATRegion {self.region_name} (Tier {self.tier_level})>"


class CATDataPoint(Base):
    """
    Individual CAT data point model
    """
    __tablename__ = 'cat_data_points'
    
    id = Column(Integer, primary_key=True)
    upload_id = Column(Integer, ForeignKey('cat_uploads.id', ondelete='CASCADE'), nullable=False)
    region_id = Column(Integer, ForeignKey('cat_regions.id', ondelete='SET NULL'), nullable=True)
    region_code = Column(String(50), nullable=True, index=True)  # Added for easier querying
    
    # Timestamp
    timestamp = Column(DateTime, nullable=True, index=True)
    
    # Location data
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, nullable=True)
    location_name = Column(String(255), nullable=True)
    
    # Access/Network metrics (for CAT analysis)
    access_type = Column(String(100), nullable=True)  # e.g., "healthcare", "education", "broadband"
    access_quality = Column(String(50), nullable=True)  # e.g., "good", "poor", "excellent"
    distance_km = Column(Float, nullable=True)  # Distance to nearest access point
    travel_time_minutes = Column(Float, nullable=True)
    
    # Network metrics
    throughput_mbps = Column(Float, nullable=True)
    latency_ms = Column(Float, nullable=True)
    jitter_ms = Column(Float, nullable=True)
    packet_loss_percent = Column(Float, nullable=True)
    signal_strength_dbm = Column(Float, nullable=True)
    
    # Technology info
    network_type = Column(String(50), nullable=True)  # 4G, 5G, WiFi, etc.
    operator = Column(String(100), nullable=True)
    
    # Status flags
    is_active = Column(Boolean, default=True)
    verified = Column(Boolean, default=False)
    
    # Additional metadata stored as JSON
    data_metadata = Column(JSON, nullable=True)
    
    # Relationships
    upload = relationship('CATUpload', back_populates='data_points')
    region = relationship('CATRegion', back_populates='data_points')
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_timestamp_region', 'timestamp', 'region_id'),
        Index('idx_location', 'latitude', 'longitude'),
        Index('idx_access_type', 'access_type'),
    )


class CATUpload(Base):
    """
    Track uploaded CAT data files (CSV/GeoJSON)
    """
    __tablename__ = 'cat_uploads'
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # 'csv' or 'geojson'
    file_size = Column(Integer, nullable=True)  # Size in bytes
    
    # Processing status
    status = Column(String(50), default='pending')  # pending, processing, completed, failed
    records_processed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # File metadata
    uploaded_by = Column(String(255), nullable=True)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    processed_date = Column(DateTime(timezone=True), nullable=True)
    
    # Processing details
    processing_details = Column(JSON, nullable=True)
    
    # Relationships
    data_points = relationship('CATDataPoint', back_populates='upload', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<CATUpload {self.filename} ({self.status})>"


class CATGatingRule(Base):
    """
    Gating rules for access control based on CAT tiers
    """
    __tablename__ = 'cat_gating_rules'
    
    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(255), nullable=False)
    tier_level = Column(Integer, nullable=False, index=True)
    
    # Access control
    min_access_score = Column(Float, nullable=True)
    max_distance_km = Column(Float, nullable=True)
    max_travel_time = Column(Float, nullable=True)
    
    # Rule configuration
    access_types = Column(JSON, nullable=True)  # List of access types allowed
    conditions = Column(JSON, nullable=True)  # Additional conditions as JSON
    
    # Status
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<CATGatingRule {self.rule_name} (Tier {self.tier_level})>"
