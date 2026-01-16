"""
Season-aware utilities for TENeT.

Alaska has dramatically different accessibility in summer vs winter:
- Winter: Many communities accessible only by air or ice roads
- Summer: Water routes open, but ice roads closed
- Year-round: Conservative baseline assuming worst-case access

These utilities help score telehealth necessity based on seasonal isolation.
"""

from enum import Enum
from typing import Dict, Optional


class Season(str, Enum):
    """Alaska seasons with transportation implications"""
    SUMMER = "summer"
    WINTER = "winter"
    YEAR_ROUND = "year_round"


# Season display names
SEASON_NAMES: Dict[Season, str] = {
    Season.SUMMER: "Summer",
    Season.WINTER: "Winter",
    Season.YEAR_ROUND: "Year-Round",
}


# Access difficulty multipliers by season
# Higher = more difficult = greater telehealth need
SEASON_DIFFICULTY: Dict[Season, float] = {
    Season.SUMMER: 1.0,      # Baseline
    Season.WINTER: 1.5,      # 50% more difficult
    Season.YEAR_ROUND: 1.25, # Average of both
}


# Transport mode availability by season
TRANSPORT_MODES: Dict[str, Dict[Season, bool]] = {
    "air": {
        Season.SUMMER: True,
        Season.WINTER: True,
        Season.YEAR_ROUND: True,
    },
    "road": {
        Season.SUMMER: True,
        Season.WINTER: False,  # Many rural roads impassable
        Season.YEAR_ROUND: False,
    },
    "water": {
        Season.SUMMER: True,
        Season.WINTER: False,  # Rivers frozen
        Season.YEAR_ROUND: False,
    },
    "ice_road": {
        Season.SUMMER: False,
        Season.WINTER: True,
        Season.YEAR_ROUND: False,
    },
}


def get_season_multiplier(season: Season) -> float:
    """
    Get difficulty multiplier for a given season.
    
    Args:
        season: The season to evaluate
        
    Returns:
        Multiplier (1.0 = baseline, higher = more difficult)
    """
    return SEASON_DIFFICULTY.get(season, 1.0)


def get_season_name(season: Season) -> str:
    """Get display name for season"""
    return SEASON_NAMES.get(season, "Unknown")


def is_transport_available(mode: str, season: Season) -> bool:
    """
    Check if a transport mode is available in a given season.
    
    Args:
        mode: Transport mode (air, road, water, ice_road)
        season: The season to check
        
    Returns:
        True if mode is available in that season
    """
    mode_lower = mode.lower()
    if mode_lower not in TRANSPORT_MODES:
        return False
    return TRANSPORT_MODES[mode_lower].get(season, False)


def calculate_seasonal_access_score(
    base_score: float,
    season: Season,
    has_road: bool = False,
    has_water: bool = False
) -> float:
    """
    Calculate season-adjusted access score.
    
    Args:
        base_score: Base access score (0-100, higher = better access)
        season: Season to adjust for
        has_road: Whether community has road access
        has_water: Whether community has water access
        
    Returns:
        Adjusted access score (0-100)
    """
    score = base_score
    
    # Apply season multiplier (inverted because higher difficulty = lower score)
    multiplier = get_season_multiplier(season)
    score = score / multiplier
    
    # Penalize if roads/water unavailable in this season
    if has_road and not is_transport_available("road", season):
        score *= 0.8  # 20% penalty
    
    if has_water and not is_transport_available("water", season):
        score *= 0.9  # 10% penalty
    
    # Clamp to 0-100
    return max(0.0, min(100.0, score))


def get_isolation_factor(season: Season, access_tier: int) -> float:
    """
    Calculate isolation factor combining season and access tier.
    
    Args:
        season: Current season
        access_tier: Community access tier (1=best, 3=worst)
        
    Returns:
        Isolation factor (0-1, higher = more isolated = greater need)
    """
    # Base isolation by tier
    tier_isolation = {
        1: 0.2,  # Well-connected
        2: 0.5,  # Moderate access
        3: 0.8,  # Very isolated
    }
    
    base = tier_isolation.get(access_tier, 0.5)
    
    # Adjust by season
    season_mult = get_season_multiplier(season)
    
    # Combine (max out at 1.0)
    return min(1.0, base * season_mult)


def parse_season(season_str: Optional[str]) -> Season:
    """
    Parse season string to enum, with fallback to YEAR_ROUND.
    
    Args:
        season_str: Season string (summer, winter, year_round)
        
    Returns:
        Season enum value
    """
    if not season_str:
        return Season.YEAR_ROUND
    
    season_str = season_str.lower().strip()
    
    if season_str in ["summer", "s"]:
        return Season.SUMMER
    elif season_str in ["winter", "w"]:
        return Season.WINTER
    else:
        return Season.YEAR_ROUND
