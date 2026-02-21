"""
Data models for TENeT community records.

Design principles:
- Raw values over derived scores
- Explicit confidence tracking
- Transparent handling of missing data
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class ConfidenceLevel(str, Enum):
    """Data confidence levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MISSING = "missing"


class Location(BaseModel):
    """Geographic coordinates"""
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")


class HealthcareData(BaseModel):
    """Healthcare facility information for a community"""
    facility_count: Optional[int] = Field(None, description="Number of healthcare facilities")
    facility_types: List[str] = Field(default_factory=list, description="Types of facilities (e.g., clinic, hospital)")
    source: str = Field(..., description="Data source (e.g., OSM, Healthsites)")
    confidence: ConfidenceLevel = Field(..., description="Confidence in data quality")
    notes: Optional[str] = Field(None, description="Additional context or caveats")
    last_updated: Optional[str] = Field(None, description="ISO timestamp of last data update")


class ConnectivityData(BaseModel):
    """Internet connectivity metrics for a community"""
    download_mbps: Optional[float] = Field(None, description="Download speed in Mbps")
    upload_mbps: Optional[float] = Field(None, description="Upload speed in Mbps")
    latency_ms: Optional[float] = Field(None, description="Network latency in milliseconds")
    source: str = Field(..., description="Data source (e.g., FCC, Ookla)")
    confidence: ConfidenceLevel = Field(..., description="Confidence in data quality")
    notes: Optional[str] = Field(None, description="Additional context or caveats")
    last_updated: Optional[str] = Field(None, description="ISO timestamp of last data update")


class AccessData(BaseModel):
    """Transportation and access information for a community"""
    transport_modes: List[str] = Field(default_factory=list, description="Available transportation methods")
    primary_access: Optional[str] = Field(None, description="Primary access method (e.g., 'air', 'road')")
    seasonal_restrictions: bool = Field(False, description="Whether access has seasonal restrictions")
    confidence: ConfidenceLevel = Field(..., description="Confidence in data quality")
    notes: Optional[str] = Field(None, description="Additional access information")


class DigitalEquityData(BaseModel):
    """
    Digital equity metrics analyzing real-world telehealth access.
    
    Shifts focus from infrastructure availability to meaningful access based on:
    - Affordability (UN Broadband Commission 2% threshold)
    - Continuity of Care (community healthcare anchors)
    - Pricing Equity (value index)
    """
    # Affordability metrics
    affordability_status: str = Field(..., description="affordable, unaffordable, or insufficient_data")
    affordability_ratio: Optional[float] = Field(None, description="Monthly cost as % of monthly income")
    monthly_income: Optional[float] = Field(None, description="Median monthly household income (USD)")
    estimated_monthly_cost: Optional[float] = Field(None, description="Estimated monthly broadband cost (USD)")
    
    # Continuity of care metrics
    nearest_facility_km: Optional[float] = Field(None, description="Distance to nearest healthcare facility")
    has_community_anchor: bool = Field(False, description="Healthcare facility within 5km")
    facility_count_5km: int = Field(0, description="Facilities within 5km radius")
    
    # Pricing equity
    value_index: Optional[float] = Field(None, description="Cost per Mbps (pricing fairness)")
    
    # Overall classification
    equity_classification: str = Field(..., description="ready, supported, excluded, or insufficient_data")
    classification_reason: str = Field(..., description="Human-readable explanation")
    
    # Metadata
    last_updated: Optional[str] = Field(None, description="ISO timestamp of analysis")
    confidence: ConfidenceLevel = Field(..., description="Confidence in equity analysis")


class CommunityRecord(BaseModel):
    """
    Complete community record with healthcare, connectivity, and access data.
    
    This is the core data structure for the TENeT system.
    No derived scores are included - only raw values and confidence indicators.
    """
    community_id: str = Field(..., description="Unique identifier (e.g., AK-XXXXX)")
    name: str = Field(..., description="Community name")
    location: Location = Field(..., description="Geographic coordinates")
    region: Optional[str] = Field(None, description="Borough or census area")
    population: Optional[int] = Field(None, description="Population estimate")
    
    healthcare: HealthcareData = Field(..., description="Healthcare facility data")
    connectivity: ConnectivityData = Field(..., description="Internet connectivity data")
    access: AccessData = Field(..., description="Transportation and access data")
    digital_equity: Optional[DigitalEquityData] = Field(None, description="Digital equity analysis (optional)")
    
    data_completeness: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Fraction of fields with high/medium confidence data (0.0-1.0)"
    )


class CommunityListItem(BaseModel):
    """Lightweight community record for list endpoints"""
    community_id: str
    name: str
    location: Location
    region: Optional[str] = None
    population: Optional[int] = None
    data_completeness: float
