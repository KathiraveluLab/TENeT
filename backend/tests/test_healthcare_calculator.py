import unittest
import sys
import os

# Ensure backend directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.healthcare_desert_calculator import HealthcareDesertCalculator
from unittest.mock import MagicMock, patch

class TestHealthcareCalculator(unittest.TestCase):
    
    @patch('services.healthcare_desert_calculator.HealthcareDesertCalculator.get_nearest_facility_distances')
    def test_calculate_healthcare_necessity_score_weights(self, mock_distances):
        """
        Verify that the Healthcare Necessity Score strictly follows the documented
        40/20/20/20 weighting split (Distance, Density, Specialist, Transport).
        """
        # Mock database session
        db = MagicMock()
        
        # 1. Distance (clinic=300km, hospital=500km) => 100 points
        # (100 * 0.40) = 40.0
        mock_distances.return_value = {'clinic': 300.0, 'hospital': 500.0}
        
        # 2. Density: 0 sites => 100 points 
        # (100 * 0.20) = 20.0
        db.query().filter().count.side_effect = [
            0,      # num_sites (density)
            False,  # has_specialists
        ]
        
        # 3. Specialist: False => 100 points
        # (100 * 0.20) = 20.0
        
        # 4. Transport: Empty mock data_point falls back to default 
        # year-round moderate => 50 points
        # (50 * 0.20) = 10.0
        db.query().filter().first.return_value = None
        
        result = HealthcareDesertCalculator.calculate_healthcare_necessity_score(db, "REGION_TEST", "year_round", "local")
        
        # Total expected: 40 + 20 + 20 + 10 = 90.0
        self.assertEqual(result['necessity_score'], 90.0)
        self.assertEqual(result['breakdown']['distance_component'], 100.0)
        self.assertEqual(result['breakdown']['density_component'], 100.0)
        self.assertEqual(result['breakdown']['specialist_component'], 100.0)
        self.assertEqual(result['breakdown']['transport_component'], 50.0)

if __name__ == '__main__':
    unittest.main()
