"""
Seed sample healthcare sites for testing
"""
from database.config import SessionLocal
from database.models import HealthcareSite


def seed_sample_healthcare_sites():
    """Add sample Alaska healthcare sites for testing"""
    
    db = SessionLocal()
    
    sample_sites = [
        {
            'name': 'Alaska Native Medical Center',
            'site_type': 'hospital',
            'latitude': 61.1947,
            'longitude': -149.8502,
            'region_code': 'AK001',  # Anchorage
            'has_emergency': True,
            'has_specialists': True,
            'services': ['emergency', 'surgery', 'primary_care', 'specialists']
        },
        {
            'name': 'Providence Alaska Medical Center',
            'site_type': 'hospital',
            'latitude': 61.1890,
            'longitude': -149.8194,
            'region_code': 'AK001',  # Anchorage
            'has_emergency': True,
            'has_specialists': True,
            'services': ['emergency', 'surgery', 'primary_care', 'cardiology']
        },
        {
            'name': 'Yukon-Kuskokwim Health Corporation',
            'site_type': 'hospital',
            'latitude': 60.7922,
            'longitude': -161.7558,
            'region_code': 'AK050',  # Bethel
            'has_emergency': True,
            'has_specialists': True,
            'services': ['emergency', 'primary_care', 'dental']
        },
        {
            'name': 'Samuel Simmonds Memorial Hospital',
            'site_type': 'hospital',
            'latitude': 71.2906,
            'longitude': -156.7886,
            'region_code': 'AK080',  # Utqiaġvik (Barrow)
            'has_emergency': True,
            'has_specialists': False,
            'services': ['emergency', 'primary_care']
        },
        {
            'name': 'Norton Sound Regional Hospital',
            'site_type': 'hospital',
            'latitude': 64.5011,
            'longitude': -165.4064,
            'region_code': 'AK060',  # Nome
            'has_emergency': True,
            'has_specialists': False,
            'services': ['emergency', 'primary_care', 'dental']
        },
        {
            'name': 'Tanana Health Clinic',
            'site_type': 'clinic',
            'latitude': 65.1717,
            'longitude': -152.0761,
            'region_code': 'AK090',  # Tanana
            'has_emergency': False,
            'has_specialists': False,
            'services': ['primary_care']
        },
        {
            'name': 'Anaktuvuk Pass Health Clinic',
            'site_type': 'clinic',
            'latitude': 68.1361,
            'longitude': -151.7431,
            'region_code': 'AK095',  # Anaktuvuk Pass
            'has_emergency': False,
            'has_specialists': False,
            'services': ['primary_care']
        },
        {
            'name': 'Fairbanks Memorial Hospital',
            'site_type': 'hospital',
            'latitude': 64.8151,
            'longitude': -147.7561,
            'region_code': 'AK002',  # Fairbanks
            'has_emergency': True,
            'has_specialists': True,
            'services': ['emergency', 'surgery', 'primary_care', 'specialists']
        },
        {
            'name': 'Bartlett Regional Hospital',
            'site_type': 'hospital',
            'latitude': 58.3577,
            'longitude': -134.5494,
            'region_code': 'AK003',  # Juneau
            'has_emergency': True,
            'has_specialists': True,
            'services': ['emergency', 'surgery', 'primary_care']
        },
        {
            'name': 'Adak Medical Clinic',
            'site_type': 'clinic',
            'latitude': 51.8800,
            'longitude': -176.6581,
            'region_code': 'AK100',  # Adak
            'has_emergency': False,
            'has_specialists': False,
            'services': ['primary_care']
        }
    ]
    
    count = 0
    for site_data in sample_sites:
        # Check if exists
        existing = db.query(HealthcareSite).filter(
            HealthcareSite.name == site_data['name']
        ).first()
        
        if not existing:
            site = HealthcareSite(**site_data)
            db.add(site)
            print(f"  ✓ Added {site_data['name']}")
            count += 1
        else:
            print(f"  - Skipped {site_data['name']} (already exists)")
    
    db.commit()
    db.close()
    
    print(f"\n✓ Healthcare sites seeding complete! Added {count} new sites.")
    return count


if __name__ == '__main__':
    seed_sample_healthcare_sites()
