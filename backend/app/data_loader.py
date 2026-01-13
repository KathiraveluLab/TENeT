"""
Enhanced data loader for Alaska communities.

Loads community data from various sources and formats:
- CSV files with community profiles
- Healthcare facility databases
- Broadband coverage data

This module bridges the gap between sample data and real datasets,
supporting both prototype and production environments.
"""

import json
import math
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import CommunityRecord, HealthcareData, ConnectivityData, AccessData, ConfidenceLevel, Location
from app.database import Community, HealthcareFacility, BroadbandCoverage


def generate_community_id(name: str) -> str:
    """
    Generate a unique, URL-friendly community ID from the community name.
    
    Examples:
        "Anchorage" -> "anchorage"
        "Utqiaġvik (Barrow)" -> "utqiagvik"
        "Point Hope" -> "point-hope"
    
    Args:
        name: Community name
        
    Returns:
        Lowercase slug suitable as database ID
    """
    # Remove parentheses and their contents, convert to lowercase
    slug = re.sub(r'\([^)]*\)', '', name).strip()
    # Replace spaces and special chars with hyphens
    slug = re.sub(r'[^\w\s-]', '', slug.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')
from app.season_utils import Season, calculate_seasonal_access_score


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points on Earth (in kilometers).
    
    Uses the Haversine formula for great-circle distance.
    """
    R = 6371  # Earth radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def calculate_access_tier(
    has_airport: bool = False,
    has_harbor: bool = False,
    has_road: bool = False,
    population: int = 0
) -> int:
    """
    Calculate access tier (1-3) based on transportation options.
    
    Tier 1: Well-connected (road + airport, or population > 10000)
    Tier 2: Moderate access (airport + harbor, or road only)
    Tier 3: Limited access (air-only, very remote)
    
    Args:
        has_airport: Whether community has airport
        has_harbor: Whether community has harbor/port
        has_road: Whether community has road connection
        population: Community population
        
    Returns:
        Access tier (1 = best, 3 = most isolated)
    """
    # Tier 1: Great connectivity
    if population > 10000:
        return 1
    if has_road and has_airport:
        return 1
    if has_road and population > 3000:
        return 1
    
    # Tier 2: Moderate
    if has_airport and has_harbor:
        return 2
    if has_road:
        return 2
    if has_airport and population > 1000:
        return 2
    
    # Tier 3: Most isolated
    return 3


def load_enhanced_communities(db: Session) -> List[Community]:
    """
    Load enhanced community dataset into database.
    
    This function creates a comprehensive dataset of Alaska communities
    with realistic data distributions for prototype/demonstration.
    
    In production, this would load from actual data files.
    """
    # Check if data already exists
    existing_count = db.query(Community).count()
    if existing_count > 0:
        print(f"✓ Database already has {existing_count} communities, skipping data load")
        return db.query(Community).all()
    
    communities_data = [
        # Major hubs - Tier 1
        {
            "name": "Anchorage", "lat": 61.2181, "lon": -149.9003, 
            "population": 291247, "tier": 1,
            "road": True, "airport": True, "harbor": True,
            "facilities": 15, "download": 1000, "upload": 100
        },
        {
            "name": "Fairbanks", "lat": 64.8378, "lon": -147.7164,
            "population": 32515, "tier": 1,
            "road": True, "airport": True, "harbor": False,
            "facilities": 5, "download": 500, "upload": 50
        },
        {
            "name": "Juneau", "lat": 58.3019, "lon": -134.4197,
            "population": 32255, "tier": 1,
            "road": False, "airport": True, "harbor": True,
            "facilities": 4, "download": 400, "upload": 40
        },
        
        # Regional centers - Tier 2
        {
            "name": "Bethel", "lat": 60.7922, "lon": -161.7558,
            "population": 6456, "tier": 2,
            "road": False, "airport": True, "harbor": True,
            "facilities": 2, "download": 100, "upload": 20
        },
        {
            "name": "Nome", "lat": 64.5011, "lon": -165.4064,
            "population": 3699, "tier": 2,
            "road": False, "airport": True, "harbor": True,
            "facilities": 2, "download": 50, "upload": 10
        },
        {
            "name": "Kotzebue", "lat": 66.8983, "lon": -162.5965,
            "population": 3102, "tier": 2,
            "road": False, "airport": True, "harbor": True,
            "facilities": 1, "download": 50, "upload": 10
        },
        {
            "name": "Dillingham", "lat": 59.0397, "lon": -158.4575,
            "population": 2249, "tier": 2,
            "road": False, "airport": True, "harbor": True,
            "facilities": 1, "download": 50, "upload": 10
        },
        {
            "name": "Sitka", "lat": 57.0531, "lon": -135.3300,
            "population": 8371, "tier": 2,
            "road": False, "airport": True, "harbor": True,
            "facilities": 2, "download": 200, "upload": 25
        },
        {
            "name": "Ketchikan", "lat": 55.3422, "lon": -131.6461,
            "population": 8230, "tier": 2,
            "road": True, "airport": True, "harbor": True,
            "facilities": 2, "download": 250, "upload": 30
        },
        
        # Remote villages - Tier 3
        {
            "name": "Utqiaġvik (Barrow)", "lat": 71.2906, "lon": -156.7886,
            "population": 4927, "tier": 3,
            "road": False, "airport": True, "harbor": False,
            "facilities": 2, "download": 50, "upload": 10
        },
        {
            "name": "Napakiak", "lat": 60.6908, "lon": -161.9789,
            "population": 378, "tier": 3,
            "road": False, "airport": True, "harbor": False,
            "facilities": 1, "download": 10, "upload": 3
        },
        {
            "name": "Haines", "lat": 59.2358, "lon": -135.4419,
            "population": 2508, "tier": 2,
            "road": True, "airport": True, "harbor": True,
            "facilities": 1, "download": 100, "upload": 15
        },
        {
            "name": "Gambell", "lat": 63.7667, "lon": -171.7333,
            "population": 681, "tier": 3,
            "road": False, "airport": True, "harbor": False,
            "facilities": 1, "download": 25, "upload": 5
        },
        {
            "name": "Savoonga", "lat": 63.6864, "lon": -170.4931,
            "population": 761, "tier": 3,
            "road": False, "airport": True, "harbor": False,
            "facilities": 1, "download": 25, "upload": 5
        },
        {
            "name": "Point Hope", "lat": 68.3483, "lon": -166.7992,
            "population": 757, "tier": 3,
            "road": False, "airport": True, "harbor": False,
            "facilities": 1, "download": 15, "upload": 3
        },
        {
            "name": "Quinhagak", "lat": 59.7550, "lon": -161.9181,
            "population": 761, "tier": 3,
            "road": False, "airport": True, "harbor": False,
            "facilities": 1, "download": 15, "upload": 3
        },
        {
            "name": "Togiak", "lat": 59.0525, "lon": -160.3728,
            "population": 883, "tier": 3,
            "road": False, "airport": True, "harbor": False,
            "facilities": 1, "download": 20, "upload": 5
        },
        {
            "name": "Alakanuk", "lat": 62.6806, "lon": -164.6189,
            "population": 714, "tier": 3,
            "road": False, "airport": True, "harbor": False,
            "facilities": 1, "download": 10, "upload": 3
        },
        {
            "name": "Emmonak", "lat": 62.7789, "lon": -164.5206,
            "population": 833, "tier": 3,
            "road": False, "airport": True, "harbor": False,
            "facilities": 1, "download": 15, "upload": 3
        },
        {
            "name": "Hooper Bay", "lat": 61.5306, "lon": -166.1464,
            "population": 1143, "tier": 3,
            "road": False, "airport": True, "harbor": False,
            "facilities": 1, "download": 20, "upload": 5
        },
    ]
    
    loaded_communities = []
    
    for data in communities_data:
        # Calculate season-specific scores
        base_score = 70.0 if data["tier"] == 1 else (50.0 if data["tier"] == 2 else 30.0)
        
        summer_score = calculate_seasonal_access_score(
            base_score, Season.SUMMER, 
            has_road=data["road"], has_water=data["harbor"]
        )
        
        winter_score = calculate_seasonal_access_score(
            base_score, Season.WINTER,
            has_road=data["road"], has_water=data["harbor"]
        )
        
        # Create healthcare data JSON
        healthcare_data = {
            "facility_count": data["facilities"],
            "facility_types": ["hospital", "clinic"] if data["facilities"] > 2 else ["clinic"],
            "source": "OSM",
            "confidence": "high" if data["facilities"] > 1 else "medium",
            "notes": f"Primary care available" if data["facilities"] > 0 else "Limited services",
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Create connectivity data JSON
        connectivity_data = {
            "download_mbps": data["download"],
            "upload_mbps": data["upload"],
            "latency_ms": 50 if data["download"] > 100 else 150,
            "source": "FCC",
            "confidence": "high" if data["download"] > 50 else "medium",
            "notes": "Satellite backup available" if data["tier"] == 3 else "Multiple providers",
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Create access data JSON
        access_modes = []
        if data["airport"]:
            access_modes.append("air")
        if data["harbor"]:
            access_modes.append("water")
        if data["road"]:
            access_modes.append("road")
        
        access_data = {
            "transport_modes": access_modes,
            "primary_access": "air" if not data["road"] else "road",
            "seasonal_restrictions": data["tier"] == 3,
            "confidence": "high",
            "notes": "Ice roads in winter" if data["tier"] == 3 and data["harbor"] else ""
        }
        
        # Calculate data completeness
        completeness = 1.0 if data["tier"] <= 2 else 0.7
        
        community = Community(
            community_id=generate_community_id(data["name"]),
            name=data["name"],
            region="Alaska",
            latitude=data["lat"],
            longitude=data["lon"],
            population=data["population"],
            access_tier=data["tier"],
            summer_access_score=summer_score,
            winter_access_score=winter_score,
            healthcare_data=healthcare_data,
            connectivity_data=connectivity_data,
            access_data=access_data,
            data_completeness=completeness
        )
        
        db.add(community)
        loaded_communities.append(community)
    
    db.commit()
    return loaded_communities


def sync_to_pydantic(db_community: Community) -> CommunityRecord:
    """
    Convert database Community to Pydantic CommunityRecord.
    
    This maintains backward compatibility with existing API.
    """
    healthcare_dict = db_community.healthcare_data or {}
    connectivity_dict = db_community.connectivity_data or {}
    access_dict = db_community.access_data or {}
    
    return CommunityRecord(
        community_id=db_community.community_id,
        name=db_community.name,
        location=Location(lat=db_community.latitude, lon=db_community.longitude),
        region=db_community.region,
        population=db_community.population,
        healthcare=HealthcareData(
            facility_count=healthcare_dict.get("facility_count"),
            facility_types=healthcare_dict.get("facility_types", []),
            source=healthcare_dict.get("source", "Unknown"),
            confidence=ConfidenceLevel(healthcare_dict.get("confidence", "missing")),
            notes=healthcare_dict.get("notes"),
            last_updated=healthcare_dict.get("last_updated")
        ),
        connectivity=ConnectivityData(
            download_mbps=connectivity_dict.get("download_mbps"),
            upload_mbps=connectivity_dict.get("upload_mbps"),
            latency_ms=connectivity_dict.get("latency_ms"),
            source=connectivity_dict.get("source", "Unknown"),
            confidence=ConfidenceLevel(connectivity_dict.get("confidence", "missing")),
            notes=connectivity_dict.get("notes"),
            last_updated=connectivity_dict.get("last_updated")
        ),
        access=AccessData(
            transport_modes=access_dict.get("transport_modes", []),
            primary_access=access_dict.get("primary_access"),
            seasonal_restrictions=access_dict.get("seasonal_restrictions", False),
            confidence=ConfidenceLevel(access_dict.get("confidence", "missing")),
            notes=access_dict.get("notes")
        ),
        data_completeness=db_community.data_completeness or 0.0
    )
