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
    def score_distance_component(distance_km: float) -> float:
        """Normalize distance to nearest facility: 0km=0, 300+km=100."""
        return min(100, (max(distance_km, 0) / 300) * 100)

    @staticmethod
    def score_density_component(num_sites: int) -> float:
        """Score facility density. Fewer facilities means higher need."""
        if num_sites <= 0:
            return 100
        if num_sites == 1:
            return 70
        if num_sites == 2:
            return 40
        return 10

    @staticmethod
    def score_specialist_component(has_specialists: bool) -> float:
        """Score specialist access. No specialists means higher need."""
        return 0 if has_specialists else 100

    @staticmethod
    def score_transport_component(
        travel_time_minutes: Optional[float],
        season: str = SEASON_YEAR_ROUND,
        road_quality: str = ROAD_QUALITY_LOCAL,
        transport_mode: str = "road",
    ) -> float:
        """Score seasonal transport difficulty on a 0-100 scale."""
        if season not in VALID_SEASONS:
            season = SEASON_YEAR_ROUND
        if road_quality not in VALID_ROAD_QUALITIES:
            road_quality = ROAD_QUALITY_LOCAL

        if not travel_time_minutes:
            if season == SEASON_WINTER:
                return 70
            if season == SEASON_SUMMER:
                return 40
            return 50

        mode = transport_mode if transport_mode in {"road", "water", "air"} else "road"
        friction = get_road_friction(road_quality, season) if mode == "road" else 1.0
        adjusted_travel_time = travel_time_minutes * friction

        modifier = get_seasonal_modifier(mode, season, road_quality)
        if modifier < 0.1:
            return 100

        availability_penalty = (1.0 - modifier) * 30
        base_transport_score = min(100, (adjusted_travel_time / 240) * 100)
        return min(100, base_transport_score + availability_penalty)

    @staticmethod
    def _region_center(db: Session, region_code: str) -> Optional[Tuple[float, float]]:
        region = db.query(CATRegion).filter(
            CATRegion.region_code == region_code
        ).first()

        if not region:
            return None

        data_points = db.query(CATDataPoint).filter(
            CATDataPoint.region_code == region_code
        ).all()

        if data_points:
            avg_lat = sum(p.latitude for p in data_points) / len(data_points)
            avg_lon = sum(p.longitude for p in data_points) / len(data_points)
            return avg_lat, avg_lon

        if region.centroid_lat is not None and region.centroid_lon is not None:
            return region.centroid_lat, region.centroid_lon

        return None

    @staticmethod
    def get_nearest_facility_distances(db: Session, region_code: str) -> Dict[str, Optional[float]]:
        """
        Calculate distances from a region center to nearest facility classes.

        Returns clinic, hospital, and nearest-facility distances in kilometers.
        """
        center = HealthcareDesertCalculator._region_center(db, region_code)
        if not center:
            return {"clinic": None, "hospital": None, "nearest": None}

        sites = db.query(HealthcareSite).filter(
            HealthcareSite.is_active == True,
            HealthcareSite.latitude.isnot(None),
            HealthcareSite.longitude.isnot(None)
        ).all()
        if not sites:
            return {"clinic": 999, "hospital": 999, "nearest": 999}

        avg_lat, avg_lon = center
        distances = {"clinic": float("inf"), "hospital": float("inf"), "nearest": float("inf")}
        clinic_types = {"clinic", "health_center", "community_health_center"}

        for site in sites:
            distance = HealthcareDesertCalculator.calculate_distance(
                avg_lat, avg_lon, site.latitude, site.longitude
            )
            distances["nearest"] = min(distances["nearest"], distance)

            site_type = (site.site_type or "").lower()
            if site_type in clinic_types:
                distances["clinic"] = min(distances["clinic"], distance)
            if site_type == "hospital":
                distances["hospital"] = min(distances["hospital"], distance)

        return {
            key: (999 if value == float("inf") else value)
            for key, value in distances.items()
        }
    
    @staticmethod
    def get_nearest_clinic_distance(db: Session, region_code: str) -> Optional[float]:
        """
        Calculate distance from region center to nearest clinic-like site.
        Returns distance in kilometers.
        """
        return HealthcareDesertCalculator.get_nearest_facility_distances(
            db, region_code
        )["clinic"]
    
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
        1. Distance to nearest clinic/hospital (50% weight)
        2. Number of health sites in region (15% weight)
        3. Specialist availability (15% weight)
        4. Transportation difficulty - season-adjusted (20% weight)
        """
        
        # 1. Distance factor (0-100) incorporates both clinic and hospital
        facility_distances = HealthcareDesertCalculator.get_nearest_facility_distances(
            db, region_code
        )
        if facility_distances["nearest"] is None:
            clinic_dist = 500.0
            hospital_dist = 500.0
            nearest_dist = 500.0
        else:
            clinic_dist = facility_distances['clinic']
            hospital_dist = facility_distances['hospital']
            nearest_dist = facility_distances['nearest']
            
        # Normalize: 0km=0 points, 300+km=100 points for clinic
        clinic_score = HealthcareDesertCalculator.score_distance_component(clinic_dist)
        # Hospital distance is more vital, scales over 500km
        hospital_score = min(100.0, (hospital_dist / 500.0) * 100.0)
        
        # Strong penalty for lacking hospital access
        distance_score = (0.6 * hospital_score) + (0.4 * clinic_score)
        
        # 2. Health site density (0-100)
        num_sites = db.query(HealthcareSite).filter(
            HealthcareSite.region_code == region_code
        ).count()
        
        density_score = HealthcareDesertCalculator.score_density_component(num_sites)
        
        # 3. Specialist availability (0-100)
        has_specialists = db.query(HealthcareSite).filter(
            HealthcareSite.region_code == region_code,
            HealthcareSite.has_specialists == True
        ).count() > 0
        
        specialist_score = HealthcareDesertCalculator.score_specialist_component(has_specialists)
        
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
        
        transport_score = HealthcareDesertCalculator.score_transport_component(
            data_point.travel_time_minutes if data_point else None,
            season,
            road_quality,
            "road",
        )
        
        # Calculate weighted score
        necessity_score = float(
            0.50 * distance_score +
            0.15 * density_score +
            0.15 * specialist_score +
            0.20 * transport_score
        )
        
        return {
            'necessity_score': round(necessity_score, 2),
            'distance_to_nearest_clinic_km': round(float(clinic_dist), 2),
            'distance_to_nearest_hospital_km': round(float(hospital_dist), 2),
            'distance_to_nearest_facility_km': round(float(nearest_dist), 2),
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
                'distance_component': round(float(distance_score), 2),  # type: ignore
                'density_component': round(float(density_score), 2),  # type: ignore
                'specialist_component': round(float(specialist_score), 2),  # type: ignore
                'transport_component': round(float(transport_score), 2),  # type: ignore
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
