"""
Healthcare Desert Calculator Service

Calculates healthcare necessity scores for regions based on:
- Distance to nearest clinic
- Number of health sites in region
- Specialist availability
- Transportation difficulty (season-adjusted)

Higher score = greater need for telehealth (0-100 scale)
"""
import math
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from database.models import HealthcareSite, CATRegion, CATDataPoint
from services.season_constants import (
    SEASON_SUMMER, SEASON_WINTER, SEASON_YEAR_ROUND, VALID_SEASONS,
    ROAD_QUALITY_LOCAL, VALID_ROAD_QUALITIES,
    get_seasonal_modifier, get_road_friction, get_season_display_name
)


class HealthcareDesertCalculator:
    """
    Calculate healthcare desert metrics for CAT regions.
    
    Necessity score ranges from 0-100:
    - 0-30: Good healthcare access
    - 31-50: Moderate access challenges
    - 51-70: Significant healthcare desert
    - 71-100: Severe healthcare desert - high telehealth priority
    """
    
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate haversine distance in km"""
        R = 6371  # Earth radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    @staticmethod
    def get_nearest_clinic_distance(db: Session, region_code: str) -> Optional[float]:
        """
        Calculate distance from region center to nearest healthcare site.
        Returns distance in kilometers.
        """
        region = db.query(CATRegion).filter(
            CATRegion.region_code == region_code
        ).first()
        
        if not region:
            return None
        
        # Get data points in region to calculate center
        data_points = db.query(CATDataPoint).filter(
            CATDataPoint.region_code == region_code
        ).all()
        
        if not data_points:
            return None
        
        # Calculate region center from data points
        avg_lat = sum(p.latitude for p in data_points) / len(data_points)
        avg_lon = sum(p.longitude for p in data_points) / len(data_points)
        
        # Find nearest healthcare site
        all_sites = db.query(HealthcareSite).all()
        
        if not all_sites:
            return 999  # No healthcare sites in database
        
        min_distance = float('inf')
        for site in all_sites:
            distance = HealthcareDesertCalculator.calculate_distance(
                avg_lat, avg_lon, site.latitude, site.longitude
            )
            min_distance = min(min_distance, distance)
        
        return min_distance
    
    @staticmethod
    def calculate_healthcare_necessity_score(
        db: Session, 
        region_code: str,
        season: str = SEASON_YEAR_ROUND,
        road_quality: str = ROAD_QUALITY_LOCAL
    ) -> Dict:
        """
        Calculate compound healthcare desert metric (0-100).
        Higher score = greater need for telehealth.
        
        Args:
            db: Database session
            region_code: The CAT region code to evaluate
            season: 'summer', 'winter', or 'year_round' (user-selected)
            road_quality: 'highway', 'local', or 'seasonal'
        
        Factors:
        1. Distance to nearest clinic (40% weight)
        2. Number of health sites in region (20% weight)
        3. Specialist availability (20% weight)
        4. Transportation difficulty - season-adjusted (20% weight)
        """
        
        # 1. Distance factor (0-100)
        distance = HealthcareDesertCalculator.get_nearest_clinic_distance(db, region_code)
        if distance is None:
            distance = 500  # Assume very remote
        
        # Normalize: 0km=0 points, 300+km=100 points
        distance_score = min(100, (distance / 300) * 100)
        
        # 2. Health site density (0-100)
        num_sites = db.query(HealthcareSite).filter(
            HealthcareSite.region_code == region_code
        ).count()
        
        # Fewer sites = higher score
        if num_sites == 0:
            density_score = 100
        elif num_sites == 1:
            density_score = 70
        elif num_sites == 2:
            density_score = 40
        else:
            density_score = 10
        
        # 3. Specialist availability (0-100)
        has_specialists = db.query(HealthcareSite).filter(
            HealthcareSite.region_code == region_code,
            HealthcareSite.has_specialists == True
        ).count() > 0
        
        specialist_score = 0 if has_specialists else 100
        
        # Validate season and road_quality inputs
        if season not in VALID_SEASONS:
            season = SEASON_YEAR_ROUND
        if road_quality not in VALID_ROAD_QUALITIES:
            road_quality = ROAD_QUALITY_LOCAL
        
        # 4. Transportation difficulty (0-100) - SEASON ADJUSTED
        # Use travel_time from CAT data points with seasonal modifiers
        data_point = db.query(CATDataPoint).filter(
            CATDataPoint.region_code == region_code
        ).first()
        
        if data_point and data_point.travel_time_minutes:
            base_travel_time = data_point.travel_time_minutes
            
            # Apply road friction multiplier
            friction = get_road_friction(road_quality, season)
            adjusted_travel_time = base_travel_time * friction
            
            # Apply seasonal availability penalty
            # Lower availability = harder to travel = higher score
            road_modifier = get_seasonal_modifier('road', season, road_quality)
            if road_modifier < 0.1:  # Route effectively unavailable
                transport_score = 100  # Maximum difficulty
            else:
                # Invert modifier: low availability = high difficulty
                availability_penalty = (1.0 - road_modifier) * 30  # Up to 30 points
                # Normalize: 0-60min=0, 240+min=100 (with adjustments)
                base_transport_score = min(100, (adjusted_travel_time / 240) * 100)
                transport_score = min(100, base_transport_score + availability_penalty)
        else:
            # Unknown travel time - use seasonal default
            if season == SEASON_WINTER:
                transport_score = 70  # Assume winter is harder
            elif season == SEASON_SUMMER:
                transport_score = 40  # Assume summer is easier
            else:
                transport_score = 50  # Year-round moderate
        
        # Calculate weighted score
        necessity_score = (
            0.40 * distance_score +
            0.20 * density_score +
            0.20 * specialist_score +
            0.20 * transport_score
        )
        
        return {
            'necessity_score': round(necessity_score, 2),
            'distance_to_nearest_clinic_km': round(distance, 2),
            'num_healthcare_sites': num_sites,
            'has_specialist_access': has_specialists,
            'avg_travel_time_minutes': data_point.travel_time_minutes if data_point else None,
            'season_scenario': {
                'active_season': season,
                'season_display': get_season_display_name(season),
                'road_quality': road_quality,
                'assumption': 'User-selected seasonal scenario for planning purposes. '
                             'Actual conditions may vary.'
            },
            'breakdown': {
                'distance_component': round(distance_score, 2),
                'density_component': round(density_score, 2),
                'specialist_component': round(specialist_score, 2),
                'transport_component': round(transport_score, 2),
                'transport_season_adjusted': True
            }
        }
    
    @staticmethod
    def get_all_region_scores(
        db: Session,
        season: str = SEASON_YEAR_ROUND,
        road_quality: str = ROAD_QUALITY_LOCAL
    ) -> list:
        """
        Get necessity scores for all regions, sorted by score (highest first).
        
        Args:
            season: 'summer', 'winter', or 'year_round'
            road_quality: 'highway', 'local', or 'seasonal'
        """
        regions = db.query(CATRegion).all()
        
        results = []
        for region in regions:
            score_data = HealthcareDesertCalculator.calculate_healthcare_necessity_score(
                db, region.region_code, season, road_quality
            )
            results.append({
                'region_code': region.region_code,
                'region_name': region.region_name,
                'cat_tier': region.tier_level,
                'necessity_score': score_data['necessity_score'],
                'num_healthcare_sites': score_data['num_healthcare_sites'],
                'has_specialist_access': score_data['has_specialist_access'],
                'season_applied': season
            })
        
        # Sort by necessity score (highest first = most in need)
        results.sort(key=lambda x: x['necessity_score'], reverse=True)
        
        return results

