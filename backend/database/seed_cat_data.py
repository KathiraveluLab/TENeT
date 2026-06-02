"""
Seed database with CAT data from preprocessed CSV.
Loads Alaska community transport profiles into CATRegion and CATDataPoint tables.
"""
import csv
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import SessionLocal
from database.models import CATRegion, CATDataPoint, CATUpload


def load_transport_profiles():
    """
    Load community transport profiles from preprocessed CSV.
    Creates CATRegion and CATDataPoint entries for each community.
    """
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'data', 'processed_data'
    )
    fixed_csv_path = os.path.join(data_dir, 'clean_transport_profiles_fixed.csv')
    csv_path = fixed_csv_path if os.path.exists(fixed_csv_path) else os.path.join(
        data_dir,
        'clean_transport_profiles_1.csv'
    )
    
    if not os.path.exists(csv_path):
        print(f"   Warning: CSV file not found at {csv_path}")
        return 0, 0
    
    db = SessionLocal()
    regions_created = 0
    data_points_created = 0
    
    try:
        db.query(CATDataPoint).delete()
        db.query(CATUpload).delete()
        db.commit()

        # First, create a seed upload record
        seed_upload = CATUpload(
            filename='clean_transport_profiles_1.csv',
            file_type='csv',
            status='completed',
            records_processed=0,
            uploaded_by='seed_script'
        )
        db.add(seed_upload)
        db.flush()  # Get the upload ID
        upload_id = seed_upload.id
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                community = row['community'].strip()
                
                # Skip empty rows
                if not community:
                    continue
                
                # Parse values
                try:
                    latitude = float(row['latitude'])
                    longitude = float(row['longitude'])
                    cat_tier = int(row['cat_tier_level'])
                    access_score = float(row['access_score'])
                except (ValueError, KeyError) as e:
                    print(f"   Skipping {community}: invalid data - {e}")
                    continue
                
                # Generate region code from community name
                clean_name = community.upper().replace(' ', '-').replace("'", "")[:20]
                region_code = f"AK-{clean_name}"
                
                # Check if region already exists
                existing_region = db.query(CATRegion).filter(
                    CATRegion.region_code == region_code
                ).first()
                
                if existing_region:
                    region = existing_region
                    region.region_name = community.title()
                    region.tier_level = cat_tier
                    region.centroid_lat = latitude
                    region.centroid_lon = longitude
                    region.access_score = access_score
                    region.properties = {
                        'tier_justification': row.get('tier_justification', ''),
                        'primary_access_modes': row.get('primary_access_modes', ''),
                        'has_airport': row.get('has_airport', 'False').lower() == 'true',
                        'has_road_access': row.get('has_road_access', 'False').lower() == 'true',
                        'has_water_access': row.get('has_water_access', 'False').lower() == 'true',
                        'coastal': row.get('coastal', 'False').lower() == 'true'
                    }
                else:
                    region = CATRegion(
                        region_code=region_code,
                        region_name=community.title(),
                        tier_level=cat_tier,
                        centroid_lat=latitude,
                        centroid_lon=longitude,
                        access_score=access_score,
                        properties={
                            'tier_justification': row.get('tier_justification', ''),
                            'primary_access_modes': row.get('primary_access_modes', ''),
                            'has_airport': row.get('has_airport', 'False').lower() == 'true',
                            'has_road_access': row.get('has_road_access', 'False').lower() == 'true',
                            'has_water_access': row.get('has_water_access', 'False').lower() == 'true',
                            'coastal': row.get('coastal', 'False').lower() == 'true'
                        }
                    )
                    db.add(region)
                    db.flush()  # Get the ID
                    regions_created += 1

                # Create CATDataPoint for this seed run
                data_point = CATDataPoint(
                    upload_id=upload_id,
                    region_id=region.id,
                    region_code=region_code,
                    latitude=latitude,
                    longitude=longitude,
                    location_name=community.title(),
                    access_type=row.get('primary_access_modes', 'unknown'),
                    access_quality=access_score,
                    data_metadata={
                        'harbordock': row.get('harbordock', 'False').lower() == 'true',
                        'stateferry': row.get('stateferry', 'False').lower() == 'true',
                        'cargobarge': row.get('cargobarge', 'False').lower() == 'true',
                        'data_collection_date': row.get('data_collection_date', '')
                    }
                )
                db.add(data_point)
                data_points_created += 1
        
        # Update the upload record with final count
        seed_upload.records_processed = data_points_created
        db.commit()
            
    except Exception as e:
        db.rollback()
        print(f"   Error loading data: {e}")
        raise
    finally:
        db.close()
    
    return regions_created, data_points_created


def seed_cat_data():
    """Main seeding function called by init_db.py"""
    print("   Loading transport profiles from CSV...")
    regions, points = load_transport_profiles()
    print(f"   ✓ Created {regions} regions and {points} data points")
    return regions, points


if __name__ == '__main__':
    print("=" * 60)
    print("Seeding CAT Data")
    print("=" * 60)
    regions, points = seed_cat_data()
    print(f"\nDone! Created {regions} regions and {points} data points.")
