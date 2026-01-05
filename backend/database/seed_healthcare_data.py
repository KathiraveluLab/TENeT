"""
Healthcare Facility Database Seeder
====================================
Seeds the healthcare_sites table with processed facility data.

Usage: python database/seed_healthcare_data.py
"""

import csv
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.config import SessionLocal, init_db
from database.models import HealthcareSite, CATRegion
from math import radians, sin, cos, sqrt, atan2


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two points using Haversine formula."""
    R = 6371  # Earth's radius in km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def find_nearest_region(db, lat: float, lon: float, regions: list) -> tuple:
    """Find the nearest CAT region to a healthcare facility."""
    min_distance = float('inf')
    nearest_region = None
    
    for region in regions:
        if region.centroid_lat and region.centroid_lon:
            dist = calculate_distance(lat, lon, region.centroid_lat, region.centroid_lon)
            if dist < min_distance:
                min_distance = dist
                nearest_region = region
    
    return (nearest_region.region_code if nearest_region else None, min_distance)


def load_facilities(csv_path: str) -> list:
    """Load processed healthcare facilities from CSV."""
    facilities = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            facilities.append(row)
    return facilities


def seed_healthcare_data():
    """Main seeding function."""
    print("=" * 60)
    print("HEALTHCARE FACILITY DATA SEEDING")
    print("=" * 60)
    
    # Initialize database
    init_db()
    db = SessionLocal()
    
    try:
        # Define paths
        script_dir = Path(__file__).parent
        csv_path = script_dir.parent / 'data' / 'processed_data' / 'healthcare_facilities.csv'
        
        if not csv_path.exists():
            print(f"Error: CSV not found at {csv_path}")
            print("Run preprocess_healthcare.py first!")
            return
        
        print(f"Loading data from: {csv_path}")
        
        # Load facilities
        facilities = load_facilities(str(csv_path))
        print(f"Found {len(facilities)} facilities to import")
        
        # Get all existing regions for matching
        regions = db.query(CATRegion).all()
        print(f"Found {len(regions)} CAT regions for matching")
        
        # Clear existing healthcare sites
        deleted = db.query(HealthcareSite).delete()
        print(f"Cleared {deleted} existing healthcare records")
        
        # Import facilities
        imported = 0
        matched_to_region = 0
        stats = {'hospital': 0, 'clinic': 0, 'pharmacy': 0, 'other': 0}
        
        for facility in facilities:
            lat = float(facility['latitude'])
            lon = float(facility['longitude'])
            
            # Find nearest region
            region_code, distance = find_nearest_region(db, lat, lon, regions)
            if region_code:
                matched_to_region += 1
            
            # Parse services
            services = facility.get('services', '').split(';') if facility.get('services') else []
            
            # Create record
            site = HealthcareSite(
                name=facility['name'] or 'Unknown Facility',
                site_type=facility['facility_type'],
                has_emergency=facility['has_emergency'].lower() == 'true',
                has_specialists=facility['has_specialists'].lower() == 'true',
                latitude=lat,
                longitude=lon,
                address=facility.get('address', ''),
                region_code=region_code,
                services=services if services else None,
                phone=facility.get('phone', ''),
                website=facility.get('website', ''),
                beds=int(facility['beds']) if facility.get('beds') and facility['beds'].isdigit() else None,
                has_telehealth=False,  # Unknown from OSM data
                is_active=True,
                verified=False  # OSM data not verified
            )
            
            db.add(site)
            imported += 1
            stats[facility['facility_type']] = stats.get(facility['facility_type'], 0) + 1
        
        db.commit()
        
        # Print summary
        print(f"\nImport complete!")
        print(f"  Imported: {imported} facilities")
        print(f"  Matched to CAT regions: {matched_to_region}")
        print(f"\nBy Type:")
        for ftype, count in sorted(stats.items(), key=lambda x: -x[1]):
            if count > 0:
                print(f"  {ftype}: {count}")
        
        print("\nDone!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    seed_healthcare_data()
