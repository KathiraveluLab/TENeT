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
    
    # Centroid coordinates for map display
    centroid_lat = Column(Float, nullable=True)
    centroid_lon = Column(Float, nullable=True)
    
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
    access_quality = Column(Float, nullable=True)  # e.g., 85.5 (0-100 scale)
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


class HealthcareSite(Base):
    """
    Healthcare facilities, clinics, hospitals for healthcare desert analysis
    """
    __tablename__ = 'healthcare_sites'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    site_type = Column(String(100), nullable=False, index=True)  # hospital, clinic, health_center
    
    # Service capabilities
    has_emergency = Column(Boolean, default=False)
    has_specialists = Column(Boolean, default=False)
    
    # Location
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(500), nullable=True)
    
    # Region association
    region_code = Column(String(50), ForeignKey('cat_regions.region_code'), nullable=True, index=True)
    
    # Services offered (stored as JSON array)
    # e.g., ["emergency", "primary_care", "specialist", "dental", "pharmacy"]
    services = Column(JSON, nullable=True)
    
    # Contact info
    phone = Column(String(50), nullable=True)
    website = Column(String(255), nullable=True)
    
    # Operating details
    operating_hours = Column(JSON, nullable=True)  # {"monday": "8:00-17:00", ...}
    beds = Column(Integer, nullable=True)  # For hospitals
    
    # Telehealth capability
    has_telehealth = Column(Boolean, default=False, index=True)
    telehealth_services = Column(JSON, nullable=True)  # ["video_consult", "remote_monitoring"]
    
    # Status
    is_active = Column(Boolean, default=True)
    verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to region
    region = relationship('CATRegion', backref='healthcare_sites')
    
    # Indexes for geospatial queries
    __table_args__ = (
        Index('idx_healthcare_location', 'latitude', 'longitude'),
        Index('idx_healthcare_type_active', 'site_type', 'is_active'),
    )
    
    def __repr__(self):
        return f"<HealthcareSite {self.name} ({self.site_type})>"


class BroadbandCoverage(Base):
    """
    FCC Broadband coverage data for Alaska communities.
    Supports the 'data coverage/confidence' layer for telehealth feasibility.
    
    Data source: FCC Broadband Availability Data
    """
    __tablename__ = 'broadband_coverage'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Place identification (FCC Census Place ID)
    place_id = Column(String(20), nullable=False, index=True)
    place_name = Column(String(255), nullable=False, index=True)
    
    # Unit count (for confidence weighting)
    residential_units = Column(Integer, nullable=True)
    
    # Coverage percentages at telehealth-relevant speed tiers
    # 25 Mbps down / 3 Mbps up - minimum for video telehealth
    any_tech_25mbps_pct = Column(Float, nullable=True)
    any_tech_100mbps_pct = Column(Float, nullable=True)
    wired_25mbps_pct = Column(Float, nullable=True)
    ngso_satellite_25mbps_pct = Column(Float, nullable=True)
    fiber_25mbps_pct = Column(Float, nullable=True)
    
    # Data quality & confidence indicators
    confidence = Column(String(20), nullable=False, default='MEDIUM')  # HIGH, MEDIUM, LOW
    data_gaps = Column(String(500), nullable=True)  # Semicolon-separated flags
    
    # Derived assessments
    telehealth_viable = Column(String(20), nullable=True)  # YES, NO, UNCERTAIN
    primary_access = Column(String(20), nullable=True)  # WIRED, SATELLITE, LIMITED
    
    # Link to CAT region (if mapping exists)
    region_code = Column(String(50), ForeignKey('cat_regions.region_code'), nullable=True, index=True)
    
    # Data source tracking
    data_source = Column(String(100), default='FCC')
    data_date = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to region
    region = relationship('CATRegion', backref='broadband_coverage')
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_broadband_place', 'place_id', 'place_name'),
        Index('idx_broadband_confidence', 'confidence'),
        Index('idx_broadband_viable', 'telehealth_viable'),
    )
    
    def __repr__(self):
        return f"<BroadbandCoverage {self.place_name} ({self.confidence})>"


class OoklaPerformance(Base):
    """
    Ookla Speedtest data for measured network performance layer.
    
    Data source: Ookla Open Data (s3://ookla-open-data/)
    Aggregated to zoom level 16 tiles (~610m x 610m at equator).
    """
    __tablename__ = 'ookla_performance'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Tile identification (Bing Maps Tile System)
    quadkey = Column(String(20), nullable=False, index=True)
    tile_x = Column(Integer, nullable=True)
    tile_y = Column(Integer, nullable=True)
    
    # Performance metrics
    avg_d_kbps = Column(Float, nullable=True)  # Average download speed (kbps)
    avg_u_kbps = Column(Float, nullable=True)  # Average upload speed (kbps)
    avg_lat_ms = Column(Float, nullable=True)  # Average latency (ms)
    
    # Sample size
    tests = Column(Integer, nullable=True)     # Number of speed tests
    devices = Column(Integer, nullable=True)   # Unique devices
    
    # Time period
    year = Column(Integer, nullable=False, index=True)
    quarter = Column(Integer, nullable=False)
    
    # Centroid coordinates for map display
    centroid_lat = Column(Float, nullable=True)
    centroid_lon = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_ookla_quadkey', 'quadkey'),
        Index('idx_ookla_location', 'centroid_lat', 'centroid_lon'),
        Index('idx_ookla_period', 'year', 'quarter'),
    )
    
    def __repr__(self):
        return f"<OoklaPerformance {self.quadkey} ({self.avg_d_kbps/1000:.1f} Mbps)>"


class CensusIncome(Base):
    """
    Census ACS income data by ZCTA (ZIP Code Tabulation Area)
    Used for affordability analysis - identifying areas where internet
    may be available but economically inaccessible.
    
    Source: US Census Bureau ACS 5-Year Estimates (B19013_001E)
    """
    __tablename__ = 'census_income'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # ZCTA identification
    zcta = Column(String(10), unique=True, nullable=False, index=True)
    state_fips = Column(String(2), nullable=True)  # '02' for Alaska
    
    # Income data
    median_income = Column(Float, nullable=True)  # Annual median household income (B19013_001E)
    income_margin_of_error = Column(Float, nullable=True)  # Margin of error
    
    # Population data
    total_households = Column(Integer, nullable=True)
    population = Column(Integer, nullable=True)
    
    # Centroid coordinates for geographic matching
    centroid_lat = Column(Float, nullable=True)
    centroid_lon = Column(Float, nullable=True)
    
    # Data metadata
    acs_year = Column(Integer, nullable=False)  # e.g., 2022 for 2018-2022 ACS 5-Year
    data_source = Column(String(100), default='ACS 5-Year Estimates')
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_census_zcta', 'zcta'),
        Index('idx_census_location', 'centroid_lat', 'centroid_lon'),
        Index('idx_census_income', 'median_income'),
    )
    
    def __repr__(self):
        return f"<CensusIncome ZCTA {self.zcta} (${self.median_income:,.0f}/yr)>"
    
    def monthly_income(self):
        """Return monthly income for affordability calculations."""
        return self.median_income / 12 if self.median_income else None
    
    def is_affordable(self, monthly_cost: float, threshold_pct: float = 2.0) -> bool:
        """
        Check if internet service at given monthly cost is affordable.
        Uses UN/ITU standard: affordable if cost < 2% of monthly income.
        """
        monthly = self.monthly_income()
        if not monthly or monthly <= 0:
            return False
        burden_pct = (monthly_cost / monthly) * 100
        return burden_pct < threshold_pct
