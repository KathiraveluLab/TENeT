
import pytest
from unittest.mock import Mock, patch
from database.models import CATDataPoint, CATGatingRule
from database.handlers import CATDataHandler

class TestCatGating:

    # happy path here check for all rules passed
    # a community with excellent metrics should pass all gating rules 

    def test_passes_all_rules(self):


        data_point = CATDataPoint(
            access_quality = 75.0,      # good access score (above 60 thershold)
            distance_km = 30.0,        # close to the nearest (below 50 thershold)
            travel_time_minutes = 45,       # quick travel (below 60 thershold)
            access_type = 'healthcare'   # allowed type
        )

        # this will simulates what would come from db 
        rules = CATGatingRule(
            rule_name = 'Tier 1 Basic Access',
            tier_level = 1,
            min_access_score = 60.0,  # data point has 75.0 = pass;
            max_distance_km = 50.0, # 30 = pass
            max_travel_time = 60, # 45 = pass
            access_types = ['healthcare' , 'education' , 'transport'],
            is_active = True,
            priority = 1
        )

        with patch.object(CATDataHandler, 'get_active_gating_rules') as mock_get_rules:
            mock_get_rules.return_value = [rules]


            result = CATDataHandler.check_access_gating(
                db = Mock(),
                data_point=data_point,
                tier_level = 1
            )
            


        assert 'allowed' in result
        assert 'failed_rules' in result
        assert 'passed_rules' in result


        assert result['allowed'] == True, 'should be allowed since all rules pass'
        assert len(result['failed_rules']) == 0, "should have no failed rules"
        assert len(result['passed_rules']) == 1, "should have one passed rule"
        assert result['passed_rules'][0] == 'Tier 1 Basic Access', " should have pass the rule"



    def test_failes_min_access_score(self):


        # suppose a community has low access score

        data_point = CATDataPoint(
            access_quality = 35.0,         # Below 60.0 threshold will FAIL
            distance_km = 30.0,           # Good distance
            travel_time_minutes = 45,    # Good travel time
            access_type = 'healthcare'    # good access type

        ) 

        rules = CATGatingRule(
            rule_name='Access Score Rule',
            tier_level=1,
            min_access_score = 60.0,      # Requires 60, but data has 35 -> FAIL
            max_distance_km = 50.0,       # Would pass if checked
            max_travel_time = 60.0,       # Would pass if checked
            access_types = ['healthcare'],
            is_active = True,
            priority = 1
        )
        
        with patch.object(CATDataHandler, 'get_active_gating_rules') as mock_get_rules:
                    mock_get_rules.return_value = [rules]
        
        
                    result = CATDataHandler.check_access_gating(
                        Mock(),
                        data_point = data_point,
                        tier_level = 1
                    )

        assert result['allowed'] == False, "should not be allowed becasue access score is too low"
        assert len(result['failed_rules']) == 1 , "should have 1 failed rule"
        assert len(result['passed_rules']) == 0, "should have no passed rules"

        failed_rule = result['failed_rules'][0]

        assert failed_rule['rule'] == 'Access Score Rule'
        assert 'Access quality 35.0 below minimum 60.0' in failed_rule['reasons'][0] 


    def test_fails_max_distance(self):

        

        data_point = CATDataPoint(
            access_quality = 75.0,        # Good score
            distance_km = 120.0,          # Far so FAIL
            travel_time_minutes = 45,     # Good travel time
            access_type = 'healthcare'
        )

        rules = CATGatingRule(
            rule_name = 'Distance Rule',
            tier_level = 1,
            min_access_score = 60.0,
            max_distance_km = 100.0,      # Data has 120 -> FAIL
            max_travel_time = 60.0,
            access_types = ['healthcare']
        )

        with patch.object(CATDataHandler, 'get_active_gating_rules') as mock_get_rules:
                    mock_get_rules.return_value = [rules]
        
        
                    result = CATDataHandler.check_access_gating(
                        Mock(),
                        data_point,
                        tier_level = 1
                    )

        assert result['allowed'] == False
        assert 'Distance 120.0km exceeds maximum 100.0km' in result['failed_rules'][0]['reasons'][0]


    def test_fails_max_travel_time(self):


        """Test: Travel time is too long"""
    
        data_point = CATDataPoint(
            access_quality = 75.0,
            distance_km = 30.0,
            travel_time_minutes = 180,    # Too long so FAIL
            access_type = 'healthcare'
        )
    
        rules = CATGatingRule(
            rule_name = 'Travel Time Rule',
            tier_level = 1,
            min_access_score = 60.0,
            max_distance_km = 50.0,
            max_travel_time = 60.0,       # Data has 180 so FAIL
            access_types = ['healthcare']
        )
    

        with patch.object(CATDataHandler, 'get_active_gating_rules') as mock_get_rules:
                    mock_get_rules.return_value = [rules]
        
        
                    result = CATDataHandler.check_access_gating(
                        Mock(),
                        data_point,
                        tier_level = 1
                    )
    
        
        assert result['allowed'] == False
        assert 'Travel time 180min exceeds maximum 60.0min' in result['failed_rules'][0]['reasons'][0]


    def test_fails_access_type(self):

        """Test: Access type is not allowed"""
    
        
        data_point = CATDataPoint(
            access_quality = 75.0,
            distance_km = 30.0,
            travel_time_minutes = 45,
            access_type = 'water'         # Not allowed -> FAIL
        )
    
        rules = CATGatingRule(
            rule_name = 'Access Type Rule',
            tier_level = 1,
            min_access_score = 60.0,
            max_distance_km = 50.0,
            max_travel_time = 60.0,
            access_types = ['healthcare', 'education', 'transport']  # 'water' not in list -> FAIL
        )
    
        with patch.object(CATDataHandler, 'get_active_gating_rules') as mock_get_rules:
                    mock_get_rules.return_value = [rules]
        
        
                    result = CATDataHandler.check_access_gating(
                        Mock(),
                        data_point,
                        tier_level = 1
                    )
    
        
        assert result['allowed'] == False
        assert "Access type 'water' not in allowed types" in result['failed_rules'][0]['reasons'][0]



        # edge cases are testing here 

    def test_multiple_rules_multiple_failures(self):

        # multiple failuers could be possible

        data_point = CATDataPoint(
            access_quality = 10.0,        # FAIL: Below 60
            distance_km = 300.0,          # FAIL: Above 50
            travel_time_minutes = 500,    # FAIL: Above 60
            access_type = 'water'         # FAIL: Not allowed

        )


        rules = CATGatingRule(
            rule_name = 'Comprehensive Rule',
            tier_level = 1,
            min_access_score = 60.0,
            max_distance_km = 50.0,
            max_travel_time = 60.0,
            access_types = ['healthcare', 'education']
        )

        with patch.object(CATDataHandler, 'get_active_gating_rules') as mock_get_rules:
                    mock_get_rules.return_value = [rules]
        
        
                    result = CATDataHandler.check_access_gating(
                        Mock(),
                        data_point,
                        tier_level = 1
                    )


        assert result['allowed'] == False
        failed_rules = result['failed_rules'][0]

        assert len(failed_rules['reasons']) == 4

        reasons = ' '.join(failed_rules['reasons'])
        assert 'Access quality 10.0 below minimum 60.0' in reasons
        assert 'Distance 300.0km exceeds maximum 50.0km' in reasons
        assert 'Travel time 500min exceeds maximum 60.0min' in reasons
        assert "Access type 'water' not in allowed types" in reasons


    def test_no_active_rules(self):
        """
        TEST CASE: No Rules Found
    
        SCENARIO: No active rules exist for this tier
        EXPECTED: allowed = True (no rules = no failures)
        """
    
        data_point = CATDataPoint(
            access_quality=75.0,
            distance_km=30.0,
            travel_time_minutes=45,
            access_type='healthcare'
        )
    
        with patch.object(CATDataHandler, 'get_active_gating_rules') as mock_get_rules:
                    mock_get_rules.return_value = []
        
        
                    result = CATDataHandler.check_access_gating(
                        Mock(),
                        data_point,
                        tier_level = 1
                    )
    
        assert result['allowed'] == True
        assert len(result['passed_rules']) == 0
        assert len(result['failed_rules']) == 0

    def test_missing_data_fields(self):
        """
        TEST CASE: Missing Data
        Some data fields are None/ Null
        Function should handle gracefully (skip checks)
        """

        data_point = CATDataPoint(
            access_quality=75.0,
            distance_km=None,           # missing data
            travel_time_minutes=None,   # missing data
            access_type='healthcare'
        )

        rules = CATGatingRule(
            rule_name='Missing Data Rule',
            tier_level=1,
            min_access_score = 60.0,
            max_distance_km = 50.0,
            max_travel_time = 60.0,
            access_types = ['healthcare']
        )

        with patch.object(CATDataHandler, 'get_active_gating_rules') as mock_get_rules:
                    mock_get_rules.return_value = [rules]
        
        
                    result = CATDataHandler.check_access_gating(
                        Mock(),
                        data_point,
                        tier_level = 1
                    )

        
        assert result['allowed'] == True
        assert len(result['failed_rules']) == 0
        assert len(result['passed_rules']) == 1


    def test_empty_access_types_in_rule(self):
        """
        TEST CASE: Rule has no access types defined

        scenario: access_types is empty or None
        expected: Access type check is skipped
        """

        
        data_point = CATDataPoint(
            access_quality = 75.0,
            distance_km = 30.0,
            travel_time_minutes = 45,
            access_type = 'unknown'       # Would normally fail, but no access_types to check
        )

        rules = CATGatingRule(
            rule_name='No Access Types Rule',
            tier_level = 1,
            min_access_score = 60.0,
            max_distance_km = 50.0,
            max_travel_time = 60.0,
            access_types = None           # No access types defined
        )

        with patch.object(CATDataHandler, 'get_active_gating_rules') as mock_get_rules:
                    mock_get_rules.return_value = [rules]
        
        
                    result = CATDataHandler.check_access_gating(
                        Mock(),
                        data_point,
                        tier_level = 1
                    )
        
        assert result['allowed'] == True
        assert len(result['failed_rules']) == 0



    # testing the priority order here
    
    
    def test_all_rules_must_pass_regardless_of_priority(self):

        """

        check_access_gating() checks EVERY rule returned  there is no
        early exit.... 'priority' only affects the ORDER rules are returned
        in (via priority.desc() in the query); 
        
        it does not mean only the highest-priority rule is checked.
        
        """

        data_point = CATDataPoint(
            access_quality=75.0, distance_km=30.0,
            travel_time_minutes=45, access_type='healthcare'
        )

        rule_high = CATGatingRule(
            rule_name='High Priority Rule', tier_level=1,
            min_access_score=60.0, max_distance_km=50.0,
            max_travel_time=60.0, access_types=['healthcare'], priority=2
        )

        rule_low = CATGatingRule(
            rule_name='Low Priority Rule (stricter)', tier_level=1,
            min_access_score=80.0,  # data has 75 -> this WILL fail
            max_distance_km=50.0, max_travel_time=60.0,
            access_types=['healthcare'], priority=1
        )

        with patch.object(CATDataHandler, 'get_active_gating_rules') as mock_get_rules:
                    mock_get_rules.return_value = [rule_high, rule_low]
        
        
                    result = CATDataHandler.check_access_gating(
                        Mock(),
                        data_point,
                        tier_level = 1
                    )

        # Even though the high priority rule passed   the low priority one
        # still gets checked and fails so overall result is NOT allowed.
        assert result['allowed'] == False
        assert 'High Priority Rule' in result['passed_rules']
        assert any(f['rule'] == 'Low Priority Rule (stricter)' for f in result['failed_rules'])


