"""
Digital Equity Layer - Validation & Testing Script

This script validates that the Digital Equity Layer is properly integrated
and functional across the entire stack.
"""

import sys
import requests
import json
from typing import Dict, List, Any


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")


def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_info(text: str):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


class TENetValidator:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.tests_passed = 0
        self.tests_failed = 0
        
    def test_api_health(self) -> bool:
        """Test if API is accessible"""
        try:
            response = requests.get(f"{self.api_url}/api/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print_success(f"API is healthy - {data.get('communities_loaded', 0)} communities loaded")
                return True
            else:
                print_error(f"API health check failed with status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print_error(f"Cannot connect to API: {e}")
            print_warning("Make sure backend is running: uvicorn app.main:app --reload --port 8000")
            return False
    
    def test_api_version(self) -> bool:
        """Test API version and features"""
        try:
            response = requests.get(self.api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                version = data.get('version', 'unknown')
                features = data.get('features', [])
                
                print_success(f"API Version: {version}")
                if version == "0.3.0":
                    print_success("Version matches Digital Equity Layer release")
                else:
                    print_warning(f"Expected version 0.3.0, got {version}")
                
                if "Digital Equity Layer" in str(features):
                    print_success("Digital Equity Layer feature advertised")
                    return True
                else:
                    print_warning("Digital Equity Layer not in features list")
                    return False
            return False
        except Exception as e:
            print_error(f"Version check failed: {e}")
            return False
    
    def test_communities_endpoint(self) -> bool:
        """Test communities listing endpoint"""
        try:
            response = requests.get(f"{self.api_url}/api/communities", timeout=5)
            if response.status_code == 200:
                communities = response.json()
                count = len(communities)
                print_success(f"Communities endpoint working - {count} communities found")
                
                if count > 0:
                    sample = communities[0]
                    print_info(f"Sample community: {sample.get('name', 'Unknown')}")
                    return True
                else:
                    print_warning("No communities found in database")
                    return False
            else:
                print_error(f"Communities endpoint failed with status {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Communities endpoint test failed: {e}")
            return False
    
    def test_digital_equity_summary(self) -> bool:
        """Test digital equity summary endpoint"""
        try:
            response = requests.get(f"{self.api_url}/api/digital-equity/summary", timeout=5)
            if response.status_code == 200:
                data = response.json()
                summary = data.get('classification_summary', {})
                stats = data.get('affordability_stats', {})
                
                print_success("Digital equity summary endpoint working")
                print_info(f"  Ready: {summary.get('ready', 0)}")
                print_info(f"  Supported: {summary.get('supported', 0)}")
                print_info(f"  Excluded: {summary.get('excluded', 0)}")
                print_info(f"  No Data: {summary.get('insufficient_data', 0)}")
                
                total = summary.get('total', 0)
                if total > 0:
                    has_data = summary.get('ready', 0) + summary.get('supported', 0) + summary.get('excluded', 0)
                    percentage = (has_data / total) * 100
                    print_info(f"  Data Coverage: {percentage:.1f}%")
                    
                    if percentage < 50:
                        print_warning("Low digital equity data coverage - consider running batch update")
                        print_info("  Run: curl -X POST http://localhost:8000/api/digital-equity/batch-update")
                    
                    return True
                else:
                    print_warning("No communities in summary")
                    return False
            else:
                print_error(f"Digital equity summary failed with status {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Digital equity summary test failed: {e}")
            return False
    
    def test_individual_community_equity(self) -> bool:
        """Test individual community digital equity endpoint"""
        try:
            # First get a community ID
            response = requests.get(f"{self.api_url}/api/communities", timeout=5)
            if response.status_code != 200:
                print_error("Could not fetch communities list")
                return False
            
            communities = response.json()
            if not communities:
                print_error("No communities available for testing")
                return False
            
            community_id = communities[0]['community_id']
            community_name = communities[0]['name']
            
            # Test digital equity endpoint
            response = requests.get(
                f"{self.api_url}/api/communities/{community_id}/digital-equity",
                timeout=5
            )
            
            if response.status_code == 200:
                equity = response.json()
                print_success(f"Digital equity data retrieved for {community_name}")
                print_info(f"  Classification: {equity.get('equity_classification', 'unknown')}")
                print_info(f"  Affordability Status: {equity.get('affordability_status', 'unknown')}")
                
                if equity.get('affordability_ratio'):
                    print_info(f"  Affordability Ratio: {equity['affordability_ratio']:.1f}%")
                
                if equity.get('value_index'):
                    print_info(f"  Value Index: ${equity['value_index']:.2f}/Mbps")
                
                if equity.get('has_community_anchor'):
                    print_info(f"  Community Anchor: Yes ({equity.get('facility_count_5km', 0)} facilities within 5km)")
                else:
                    print_info("  Community Anchor: No")
                
                return True
            elif response.status_code == 500:
                print_warning(f"Digital equity data not available for {community_name}")
                print_info("This may be normal if equity data hasn't been computed yet")
                print_info("Run: python backend/migrate_digital_equity.py --populate")
                return False
            else:
                print_error(f"Digital equity endpoint failed with status {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Individual community equity test failed: {e}")
            return False
    
    def test_community_data_structure(self) -> bool:
        """Test that community data includes digital equity field"""
        try:
            response = requests.get(f"{self.api_url}/api/communities", timeout=5)
            if response.status_code != 200:
                return False
            
            communities = response.json()
            if not communities:
                return False
            
            # Get full community data
            community_id = communities[0]['community_id']
            response = requests.get(f"{self.api_url}/api/communities/{community_id}", timeout=5)
            
            if response.status_code == 200:
                community = response.json()
                has_equity = 'digital_equity' in community
                
                if has_equity and community['digital_equity']:
                    print_success("Community records include digital_equity field")
                    return True
                elif has_equity:
                    print_warning("digital_equity field exists but is null")
                    print_info("Run equity data population to fill this field")
                    return False
                else:
                    print_error("digital_equity field missing from community records")
                    print_info("Database migration may be needed")
                    return False
            return False
        except Exception as e:
            print_error(f"Data structure test failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all validation tests"""
        print_header("TENeT Digital Equity Layer Validation")
        
        tests = [
            ("API Health Check", self.test_api_health),
            ("API Version & Features", self.test_api_version),
            ("Communities Endpoint", self.test_communities_endpoint),
            ("Digital Equity Summary", self.test_digital_equity_summary),
            ("Individual Community Equity", self.test_individual_community_equity),
            ("Data Structure Validation", self.test_community_data_structure),
        ]
        
        results = []
        for name, test_func in tests:
            print_header(name)
            try:
                result = test_func()
                results.append((name, result))
                if result:
                    self.tests_passed += 1
                else:
                    self.tests_failed += 1
            except Exception as e:
                print_error(f"Test crashed: {e}")
                results.append((name, False))
                self.tests_failed += 1
        
        # Print summary
        print_header("Validation Summary")
        total = self.tests_passed + self.tests_failed
        percentage = (self.tests_passed / total * 100) if total > 0 else 0
        
        print(f"\n{Colors.BOLD}Results:{Colors.END}")
        print(f"  {Colors.GREEN}Passed: {self.tests_passed}{Colors.END}")
        print(f"  {Colors.RED}Failed: {self.tests_failed}{Colors.END}")
        print(f"  {Colors.BLUE}Success Rate: {percentage:.1f}%{Colors.END}\n")
        
        if self.tests_passed == total:
            print_success("🎉 All tests passed! Digital Equity Layer is fully functional.")
            return 0
        elif self.tests_passed > 0:
            print_warning("⚠️  Some tests failed. Check logs above for details.")
            return 1
        else:
            print_error("❌ All tests failed. System is not functional.")
            print_info("\nTroubleshooting steps:")
            print_info("1. Make sure backend is running: uvicorn app.main:app --reload --port 8000")
            print_info("2. Run database migration: python backend/migrate_digital_equity.py --populate")
            print_info("3. Check backend logs for errors")
            return 2


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate TENeT Digital Equity Layer")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Backend API URL (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    validator = TENetValidator(args.api_url)
    exit_code = validator.run_all_tests()
    sys.exit(exit_code)
