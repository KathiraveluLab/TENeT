"""
Seed script to import processed broadband data into the database.

Reads from: ../data/processed_data/broadband_data_gaps.csv
Imports into: broadband_coverage table

Run with: python database/seed_broadband_data.py
"""

import os
import sys
import csv
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import SessionLocal, engine, Base
from database.models import BroadbandCoverage, CATRegion


def seed_broadband_data():
    """Import broadband data from preprocessed CSV into database."""
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Path to preprocessed data
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'processed_data', 'broadband_data_gaps.csv'
        )
        
        if not os.path.exists(data_path):
            print(f"Error: Data file not found at {data_path}")
            print("Run the preprocessing script first: python data/scripts/preprocess_broadband.py")
            return
        
        print(f"Loading data from: {data_path}")
        
        # Get existing region codes for potential mapping
        existing_regions = {r.region_code: r for r in db.query(CATRegion).all()}
        print(f"Found {len(existing_regions)} existing CAT regions")
        
        # Clear existing broadband data
        existing_count = db.query(BroadbandCoverage).count()
        if existing_count > 0:
            print(f"Clearing {existing_count} existing broadband records...")
            db.query(BroadbandCoverage).delete()
            db.commit()
        
        # Read and import CSV data
        imported_count = 0
        skipped_count = 0
        
        with open(data_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    # Parse numeric fields
                    any_tech_25 = float(row['any_tech_25mbps_pct']) if row['any_tech_25mbps_pct'] else None
                    any_tech_100 = float(row['any_tech_100mbps_pct']) if row['any_tech_100mbps_pct'] else None
                    wired_25 = float(row['wired_25mbps_pct']) if row['wired_25mbps_pct'] else None
                    ngso_25 = float(row['ngso_satellite_25mbps_pct']) if row['ngso_satellite_25mbps_pct'] else None
                    fiber_25 = float(row['fiber_25mbps_pct']) if row['fiber_25mbps_pct'] else None
                    units = int(row['residential_units']) if row['residential_units'] else None
                    
                    # Try to find matching CAT region
                    region_code = None
                    place_name = row['place_name']
                    
                    # Try exact match on region name
                    for code, region in existing_regions.items():
                        if region.region_name and place_name.lower() in region.region_name.lower():
                            region_code = code
                            break
                    
                    # Create broadband coverage record
                    coverage = BroadbandCoverage(
                        place_id=str(row['place_id']),
                        place_name=place_name,
                        residential_units=units,
                        any_tech_25mbps_pct=any_tech_25,
                        any_tech_100mbps_pct=any_tech_100,
                        wired_25mbps_pct=wired_25,
                        ngso_satellite_25mbps_pct=ngso_25,
                        fiber_25mbps_pct=fiber_25,
                        confidence=row['confidence'],
                        data_gaps=row['data_gaps'] if row['data_gaps'] != 'NONE' else None,
                        telehealth_viable=row['telehealth_viable'],
                        primary_access=row['primary_access'],
                        region_code=region_code,
                        data_source='FCC',
                        data_date=datetime.now()
                    )
                    
                    db.add(coverage)
                    imported_count += 1
                    
                except Exception as e:
                    print(f"Error importing row {row.get('place_name', 'unknown')}: {e}")
                    skipped_count += 1
                    continue
            
            db.commit()
        
        print(f"\nImport complete!")
        print(f"  Imported: {imported_count} places")
        print(f"  Skipped:  {skipped_count} places")
        
        # Print summary statistics
        print(f"\nData Summary:")
        
        # By confidence
        for conf in ['HIGH', 'MEDIUM', 'LOW']:
            count = db.query(BroadbandCoverage).filter(
                BroadbandCoverage.confidence == conf
            ).count()
            print(f"  {conf} confidence: {count}")
        
        # By telehealth viability
        for viable in ['YES', 'NO', 'UNCERTAIN']:
            count = db.query(BroadbandCoverage).filter(
                BroadbandCoverage.telehealth_viable == viable
            ).count()
            print(f"  Telehealth {viable}: {count}")
        
        # By primary access
        for access in ['WIRED', 'SATELLITE', 'LIMITED']:
            count = db.query(BroadbandCoverage).filter(
                BroadbandCoverage.primary_access == access
            ).count()
            print(f"  Primary {access}: {count}")
        
        # Places with data gaps
        gaps_count = db.query(BroadbandCoverage).filter(
            BroadbandCoverage.data_gaps.isnot(None)
        ).count()
        print(f"  Places with data gaps: {gaps_count}")
        
        # Matched to CAT regions
        matched_count = db.query(BroadbandCoverage).filter(
            BroadbandCoverage.region_code.isnot(None)
        ).count()
        print(f"  Matched to CAT regions: {matched_count}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    
    finally:
        db.close()


if __name__ == '__main__':
    print("=" * 60)
    print("BROADBAND DATA SEEDING")
    print("=" * 60)
    seed_broadband_data()
    print("\nDone!")
