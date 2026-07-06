import sys
import os
import pytest

# Ensure backend directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.cat_routes import _calculate_seasonal_tier

@pytest.mark.parametrize("base_tier, base_score, properties, expected_tier, expected_score", [
    # Test 1: Tier 1 (Road + Water + Air) -> Stays Tier 1, minor penalties
    (1, 100.0, {'primary_access_modes': 'road,water,air'}, 1, 85.0), 
    
    # Test 2: Tier 1 (Road + Water, No Air) -> Drops to Tier 3, heavy score penalty
    (1, 90.0, {'primary_access_modes': 'road,water'}, 3, 40.0), 
    
    # Test 3: Tier 3 (Road only, No Air) -> Stays Tier 3 (Fixes the road-only bug!)
    (3, 80.0, {'primary_access_modes': 'road'}, 3, 55.0), 
    
    # Test 4: Tier 3 (Water only, No Air) -> Drops to Tier 4
    (3, 70.0, {'primary_access_modes': 'water'}, 4, 25.0), 
    
    # Test 5: Tier 4 (No road, no water, no air) -> Stays Tier 4, receives -20 penalty intentionally
    (4, 50.0, {'primary_access_modes': ''}, 4, 30.0), 
    
    # Test 6: Tier 2 (Air only) -> Stays Tier 2
    (2, 90.0, {'primary_access_modes': 'air'}, 2, 90.0)
])
def test_calculate_seasonal_tier_winter(base_tier, base_score, properties, expected_tier, expected_score):
    """
    Test winter penalty matrix across all tiers to verify road-only bug fix 
    and consistent application of the 20-point no-air penalty.
    """
    adjusted_tier, adjusted_score, explanation = _calculate_seasonal_tier(
        base_tier, base_score, properties, 'winter'
    )
    
    assert adjusted_tier == expected_tier
    assert adjusted_score == expected_score
