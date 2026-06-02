"""
Initialize database and create sample data
Run this script to set up the database with sample CAT data
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import init_db, SessionLocal
from database.models import CATGatingRule
from database.handlers import (
    CATDataHandler,
    CAT4_MIN_BANDWIDTH_MBPS,
    CAT4_MAX_LATENCY_MS,
    CAT4_MIN_ACCESS_SCORE,
    CAT4_VIDEO_MIN_BANDWIDTH_MBPS,
    CAT4_VIDEO_MAX_LATENCY_MS,
    CAT4_STORE_FORWARD_MIN_BANDWIDTH_MBPS
)

def create_sample_gating_rules(db):
    """Create sample gating rules for each tier"""
    db.query(CATGatingRule).delete()
    db.commit()

    rules = [
        {
            'rule_name': 'Tier 1 Basic Access',
            'tier_level': 1,
            'min_access_score': 60.0,
            'max_distance_km': 50.0,
            'max_travel_time': 60.0,
            'access_types': ['healthcare', 'education', 'transport'],
            'is_active': True,
            'priority': 1
        },
        {
            'rule_name': 'Tier 2 Moderate Access',
            'tier_level': 2,
            'min_access_score': 40.0,
            'max_distance_km': 100.0,
            'max_travel_time': 120.0,
            'access_types': ['healthcare', 'education', 'transport', 'internet'],
            'is_active': True,
            'priority': 2
        },
        {
            'rule_name': 'Tier 3 Limited Access',
            'tier_level': 3,
            'min_access_score': 20.0,
            'max_distance_km': 200.0,
            'max_travel_time': 180.0,
            'access_types': ['healthcare', 'education', 'transport', 'internet', 'emergency'],
            'is_active': True,
            'priority': 3
        },
        {
            'rule_name': 'Tier 4 Extreme Access',
            'tier_level': 4,
            'min_access_score': CAT4_MIN_ACCESS_SCORE,
            'max_distance_km': 500.0,       # Fly-in only communities
            'max_travel_time': 480.0,       # 8 hours (weather-dependent)
            'access_types': ['healthcare', 'emergency', 'telehealth'],
            'conditions': {
                'min_bandwidth_mbps': CAT4_MIN_BANDWIDTH_MBPS,
                'max_latency_ms': CAT4_MAX_LATENCY_MS,
                'satellite_dependent': True,
                'telehealth_modes': {
                    'video': {
                        'min_bandwidth_mbps': CAT4_VIDEO_MIN_BANDWIDTH_MBPS,
                        'max_latency_ms': CAT4_VIDEO_MAX_LATENCY_MS
                    },
                    'audio': {
                        'min_bandwidth_mbps': CAT4_MIN_BANDWIDTH_MBPS,
                        'max_latency_ms': CAT4_MAX_LATENCY_MS
                    },
                    'store_forward': {
                        'min_bandwidth_mbps': CAT4_STORE_FORWARD_MIN_BANDWIDTH_MBPS
                    }
                }
            },
            'is_active': True,
            'priority': 4
        }
    ]

    
    for rule_data in rules:
        try:
            CATDataHandler.create_gating_rule(db, rule_data)
            print(f"Created gating rule: {rule_data['rule_name']}")
        except Exception as e:
            print(f"Error creating rule {rule_data['rule_name']}: {e}")

def main():
    print("=" * 60)
    print("TENeT Database Initialization")
    print("=" * 60)
    
    # Initialize database
    print("\n1. Initializing database tables...")
    init_db()
    print("✓ Database tables created")
    
    # Create sample gating rules
    print("\n2. Creating sample gating rules...")
    db = SessionLocal()
    try:
        create_sample_gating_rules(db)
        print("✓ Sample gating rules created")
    finally:
        db.close()
    
    # Seed CAT data from preprocessed CSV first so other datasets can map to regions
    print("\n3. Seeding CAT regions and data points...")
    try:
        from database.seed_cat_data import seed_cat_data
        seed_cat_data()
    except Exception as e:
        print(f"   Warning: Could not seed CAT data: {e}")
    
    print("\n4. Seeding healthcare facilities...")
    try:
        from database.seed_healthcare_data import seed_healthcare_data
        seed_healthcare_data()
    except Exception as e:
        print(f"   Warning: Could not seed healthcare facilities: {e}")

    print("\n5. Seeding broadband coverage...")
    try:
        from database.seed_broadband_data import seed_broadband_data
        seed_broadband_data()
    except Exception as e:
        print(f"   Warning: Could not seed broadband coverage: {e}")

    print("\n6. Seeding sample Census income...")
    try:
        from database.seed_census_data import seed_census_data
        seed_census_data()
    except Exception as e:
        print(f"   Warning: Could not seed Census income: {e}")

    print("\n7. Seeding sample Ookla performance...")
    try:
        from database.seed_ookla_sample_data import seed_ookla_sample_data
        seed_ookla_sample_data()
    except Exception as e:
        print(f"   Warning: Could not seed Ookla performance: {e}")
    
    # Get statistics
    print("\n8. Database Statistics:")
    db = SessionLocal()
    try:
        stats = CATDataHandler.get_statistics(db)
        print(f"   - Total regions: {stats['total_regions']}")
        print(f"   - Total data points: {stats['total_data_points']}")
        print(f"   - Total uploads: {stats['total_uploads']}")
        print(f"   - Completed uploads: {stats['completed_uploads']}")
        print(f"   - Total gating rules: {stats['total_gating_rules']}")
        print(f"   - Active gating rules: {stats['active_gating_rules']}")
        print(f"   - Total healthcare sites: {stats.get('total_healthcare_sites', 0)}")
        print(f"   - Hospitals: {stats.get('hospitals', 0)}")
        print(f"   - Clinics: {stats.get('clinics', 0)}")
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("✓ Database initialization completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start the backend: python app.py")
    print("2. View statistics: GET /api/cat/statistics")
    print("3. View healthcare sites: GET /api/cat/healthcare-sites")
    print("\nSample data templates are available in data/samples/")
    print("=" * 60)

if __name__ == '__main__':
    main()
