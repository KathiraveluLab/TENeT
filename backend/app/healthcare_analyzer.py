"""
Healthcare access analysis service.

Calculates healthcare necessity scores based on:
- Distance to nearest healthcare facility
- Population size
- Facility availability
- Season-adjusted accessibility

Higher necessity score = greater need for telehealth intervention.
"""

import math
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session

from app.database import Community, HealthcareFacility
from app.season_utils import Season, get_isolation_factor


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points (in kilometers).
    
    Uses Haversine formula.
    """
    R = 6371  # Earth radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def find_nearest_facilities(
    community: Community,
    facilities: List[HealthcareFacility],
    limit: int = 3
) -> List[Tuple[HealthcareFacility, float]]:
    """
    Find nearest healthcare facilities to a community.
    
    Args:
        community: The community to analyze
        facilities: List of all healthcare facilities
        limit: Maximum number of facilities to return
        
    Returns:
        List of (facility, distance_km) tuples, sorted by distance
    """
    distances = []
    
    for facility in facilities:
        dist = calculate_distance(
            community.latitude, community.longitude,
            facility.latitude, facility.longitude
        )
        distances.append((facility, dist))
    
    # Sort by distance and return top N
    distances.sort(key=lambda x: x[1])
    return distances[:limit]


def calculate_necessity_score(
    community: Community,
    nearest_distance_km: float,
    facility_count_local: int,
    season: Season = Season.YEAR_ROUND
) -> float:
    """
    Calculate healthcare necessity score (0-100).
    
    Higher score indicates greater need for telehealth services.
    
    Factors considered:
    - Distance to nearest facility
    - Number of local facilities
    - Population size
    - Season-adjusted access difficulty
    
    Score ranges:
    - 0-30: Good healthcare access, low telehealth necessity
    - 31-50: Moderate access challenges
    - 51-70: Significant healthcare desert
    - 71-100: Severe healthcare desert - critical telehealth need
    
    Args:
        community: Community to analyze
        nearest_distance_km: Distance to nearest healthcare facility
        facility_count_local: Number of facilities in/near community
        season: Season to adjust for (affects travel difficulty)
        
    Returns:
        Necessity score (0-100)
    """
    score = 0.0
    
    # 1. Distance component (0-40 points)
    # Exponential penalty for distance
    if nearest_distance_km <= 10:
        distance_score = 5
    elif nearest_distance_km <= 50:
        distance_score = 15
    elif nearest_distance_km <= 100:
        distance_score = 25
    elif nearest_distance_km <= 200:
        distance_score = 35
    else:
        distance_score = 40
    
    score += distance_score
    
    # 2. Facility availability (0-30 points)
    # Inverse relationship: fewer facilities = higher score
    if facility_count_local == 0:
        facility_score = 30
    elif facility_count_local == 1:
        facility_score = 20
    elif facility_count_local == 2:
        facility_score = 10
    else:
        facility_score = 5
    
    score += facility_score
    
    # 3. Population pressure (0-15 points)
    # Small populations with limited facilities need telehealth more
    population = community.population or 1000
    if population < 500:
        pop_score = 15
    elif population < 1000:
        pop_score = 12
    elif population < 3000:
        pop_score = 8
    elif population < 10000:
        pop_score = 5
    else:
        pop_score = 0
    
    score += pop_score
    
    # 4. Season adjustment (0-15 points)
    # Use access tier and season to calculate isolation
    tier = community.access_tier or 2
    isolation = get_isolation_factor(season, tier)
    season_score = isolation * 15
    
    score += season_score
    
    # Clamp to 0-100
    return max(0.0, min(100.0, score))


def analyze_community_healthcare(
    db: Session,
    community_id: str,
    season: Season = Season.YEAR_ROUND
) -> dict:
    """
    Comprehensive healthcare access analysis for a community.
    
    Args:
        db: Database session
        community_id: Community ID to analyze
        season: Season for access adjustment
        
    Returns:
        Dictionary with analysis results:
        - necessity_score: 0-100 score
        - nearest_facility: Name and distance
        - local_facility_count: Number of nearby facilities
        - priority_level: CRITICAL/HIGH/MODERATE/LOW
        - recommendation: Text recommendation
    """
    # Get community
    community = db.query(Community).filter(
        Community.community_id == community_id
    ).first()
    
    if not community:
        return {"error": "Community not found"}
    
    # Get all facilities
    all_facilities = db.query(HealthcareFacility).all()
    
    # Find nearest facilities
    nearest = find_nearest_facilities(community, all_facilities, limit=3)
    
    # Count local facilities (within 50km)
    local_count = sum(1 for _, dist in nearest if dist <= 50)
    
    # Get nearest distance
    nearest_distance = nearest[0][1] if nearest else 999.0
    nearest_name = nearest[0][0].name if nearest else "None"
    
    # Calculate necessity score
    necessity = calculate_necessity_score(
        community, nearest_distance, local_count, season
    )
    
    # Determine priority level
    if necessity >= 71:
        priority = "CRITICAL"
        color = "#8B0000"  # Dark red
    elif necessity >= 51:
        priority = "HIGH"
        color = "#FF6B6B"  # Red
    elif necessity >= 31:
        priority = "MODERATE"
        color = "#FFD93D"  # Yellow
    else:
        priority = "LOW"
        color = "#6BCF7F"  # Green
    
    # Generate recommendation
    if priority == "CRITICAL":
        recommendation = "Immediate telehealth infrastructure needed. Very limited local healthcare access."
    elif priority == "HIGH":
        recommendation = "Strong candidate for telehealth services. Significant travel required for care."
    elif priority == "MODERATE":
        recommendation = "Telehealth would improve access. Some healthcare facilities available."
    else:
        recommendation = "Good healthcare access. Telehealth can supplement existing services."
    
    return {
        "community_id": community_id,
        "community_name": community.name,
        "necessity_score": round(necessity, 1),
        "nearest_facility": {
            "name": nearest_name,
            "distance_km": round(nearest_distance, 1),
            "type": nearest[0][0].facility_type if nearest else "unknown"
        },
        "local_facility_count": local_count,
        "priority_level": priority,
        "priority_color": color,
        "recommendation": recommendation,
        "season": season.value,
        "access_tier": community.access_tier
    }
