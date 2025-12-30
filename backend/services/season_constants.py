"""
Season-Aware Access Constants for TENeT

This module defines explicit, lookup-based modifiers for seasonal transport
availability and road quality friction. All values are deterministic and
explainable - no ML or probabilistic modeling.

DESIGN NOTES:
- Season is user-selected via frontend, not auto-detected
- Winter conservatively penalizes seasonal transport modes
- Road quality affects travel friction, not binary access
- All assumptions are explicit for policy interpretation
"""

from typing import Dict, List

# =============================================================================
# Season Modes
# =============================================================================

SEASON_SUMMER = 'summer'
SEASON_WINTER = 'winter'
SEASON_YEAR_ROUND = 'year_round'

VALID_SEASONS: List[str] = [SEASON_SUMMER, SEASON_WINTER, SEASON_YEAR_ROUND]

# =============================================================================
# Road Quality Classifications
# =============================================================================
# Based on Alaska DOT general categories, simplified for prototype

ROAD_QUALITY_HIGHWAY = 'highway'    # Year-round maintained (e.g., Parks Hwy)
ROAD_QUALITY_LOCAL = 'local'        # Paved/gravel, may have winter issues
ROAD_QUALITY_SEASONAL = 'seasonal'  # Ice roads, summer-only routes

VALID_ROAD_QUALITIES: List[str] = [
    ROAD_QUALITY_HIGHWAY,
    ROAD_QUALITY_LOCAL,
    ROAD_QUALITY_SEASONAL
]

# =============================================================================
# Seasonal Transport Availability Modifiers
# =============================================================================
# These modifiers represent the fraction of "normal" availability (0.0 to 1.0)
# Applied to the transport difficulty component of healthcare desert scores

TRANSPORT_SEASONAL_MODIFIERS: Dict[str, Dict[str, float]] = {
    SEASON_SUMMER: {
        'air': 1.0,             # Full availability - long daylight
        'road_highway': 1.0,    # Fully maintained
        'road_local': 1.0,      # Generally accessible
        'road_seasonal': 1.0,   # Open in summer
        'water': 1.0,           # Ice-free navigation
    },
    SEASON_WINTER: {
        'air': 0.7,             # Weather delays, reduced visibility
        'road_highway': 0.9,    # Plowed, but conditions vary
        'road_local': 0.5,      # Often icy, delayed plowing
        'road_seasonal': 0.0,   # Closed - unavailable
        'water': 0.1,           # Mostly ice-blocked (rare icebreaker routes)
    },
    SEASON_YEAR_ROUND: {
        # Conservative average considering worst-case periods
        'air': 0.85,
        'road_highway': 0.95,
        'road_local': 0.75,
        'road_seasonal': 0.5,   # Half the year available
        'water': 0.55,          # Roughly 5-6 months navigable
    }
}

# =============================================================================
# Road Quality Friction Multipliers
# =============================================================================
# Applied to travel time/difficulty calculations
# Higher = more difficult travel (1.0 is baseline)

ROAD_QUALITY_FRICTION: Dict[str, float] = {
    ROAD_QUALITY_HIGHWAY: 1.0,   # Baseline - well-maintained
    ROAD_QUALITY_LOCAL: 1.3,     # 30% harder - variable conditions
    ROAD_QUALITY_SEASONAL: 1.6,  # 60% harder - rough/unmaintained when open
}

# =============================================================================
# Winter-Specific Road Penalties
# =============================================================================
# Additional friction applied to road types during winter

WINTER_ROAD_PENALTY: Dict[str, float] = {
    ROAD_QUALITY_HIGHWAY: 1.1,   # 10% penalty - ice/snow
    ROAD_QUALITY_LOCAL: 1.5,     # 50% penalty - poor plowing
    ROAD_QUALITY_SEASONAL: 2.0,  # Double difficulty if somehow accessible
}

# =============================================================================
# Helper Functions
# =============================================================================

def get_seasonal_modifier(
    transport_mode: str,
    season: str,
    road_quality: str = ROAD_QUALITY_LOCAL
) -> float:
    """
    Get the combined seasonal availability modifier for a transport mode.
    
    Args:
        transport_mode: 'air', 'road', or 'water'
        season: One of VALID_SEASONS
        road_quality: One of VALID_ROAD_QUALITIES (only applies to road)
    
    Returns:
        Float modifier between 0.0 and 1.0
    """
    if season not in VALID_SEASONS:
        season = SEASON_YEAR_ROUND  # Safe default
    
    modifiers = TRANSPORT_SEASONAL_MODIFIERS[season]
    
    if transport_mode == 'air':
        return modifiers['air']
    elif transport_mode == 'water':
        return modifiers['water']
    elif transport_mode == 'road':
        # Get road-type specific modifier
        road_key = f'road_{road_quality}'
        if road_key in modifiers:
            return modifiers[road_key]
        return modifiers['road_local']  # Default to local
    else:
        return 0.5  # Unknown mode - conservative


def get_road_friction(road_quality: str, season: str) -> float:
    """
    Get the travel friction multiplier for a road type and season.
    
    Args:
        road_quality: One of VALID_ROAD_QUALITIES
        season: One of VALID_SEASONS
    
    Returns:
        Float multiplier >= 1.0 (higher = more difficult)
    """
    if road_quality not in VALID_ROAD_QUALITIES:
        road_quality = ROAD_QUALITY_LOCAL
    
    base_friction = ROAD_QUALITY_FRICTION[road_quality]
    
    # Apply winter penalty
    if season == SEASON_WINTER:
        winter_penalty = WINTER_ROAD_PENALTY.get(road_quality, 1.0)
        return base_friction * winter_penalty
    
    return base_friction


def get_season_display_name(season: str) -> str:
    """Get human-readable name for a season."""
    return {
        SEASON_SUMMER: 'Summer',
        SEASON_WINTER: 'Winter',
        SEASON_YEAR_ROUND: 'Year-Round Average'
    }.get(season, 'Unknown')
