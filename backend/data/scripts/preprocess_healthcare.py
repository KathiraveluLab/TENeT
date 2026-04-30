"""
Healthcare Facility Data Preprocessing Script
==============================================
This script cleans and preprocesses the OSM healthcare GeoJSON data
to support distance calculations for telehealth feasibility analysis.

Input: ../raw/alaska_healthsites.geojson
Output: ../processed_data/healthcare_facilities.csv
        ../processed_data/healthcare_summary.csv

Data Source: OpenStreetMap via Overpass Turbo
"""

import json
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

# Healthcare facility types to include
FACILITY_TYPES = {
    'hospital': 'hospital',
    'clinic': 'clinic',
    'doctors': 'clinic',
    'doctor': 'clinic',
    'pharmacy': 'pharmacy',
    'dentist': 'clinic',
    'health_centre': 'health_center',
    'health_center': 'health_center',
    'nursing_home': 'nursing_home'
}


def load_geojson(filepath: str) -> dict:
    """Load the GeoJSON file."""
    print(f"Loading GeoJSON from: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"   Loaded {len(data.get('features', []))} features")
    return data


def get_centroid(geometry: dict) -> tuple:
    """
    Calculate centroid from geometry.
    Handles Point, Polygon, and MultiPolygon geometries.
    """
    geo_type = geometry.get('type', '')
    coords = geometry.get('coordinates', [])
    
    if geo_type == 'Point':
        return (coords[1], coords[0])  # lat, lon
    
    elif geo_type == 'Polygon':
        # Get first ring (outer boundary)
        ring = coords[0] if coords else []
        if not ring:
            return (None, None)
        # Calculate centroid as average of all points
        lons = [p[0] for p in ring]
        lats = [p[1] for p in ring]
        return (sum(lats) / len(lats), sum(lons) / len(lons))
    
    elif geo_type == 'MultiPolygon':
        # Use first polygon
        if coords and coords[0]:
            ring = coords[0][0]
            if ring:
                lons = [p[0] for p in ring]
                lats = [p[1] for p in ring]
                return (sum(lats) / len(lats), sum(lons) / len(lons))
    
    return (None, None)


def parse_address(props: dict) -> str:
    """Build address string from OSM address fields."""
    parts = []
    if props.get('addr:housenumber'):
        parts.append(props['addr:housenumber'])
    if props.get('addr:street'):
        parts.append(props['addr:street'])
    if props.get('addr:city'):
        parts.append(props['addr:city'])
    if props.get('addr:state'):
        parts.append(props['addr:state'])
    if props.get('addr:postcode'):
        parts.append(props['addr:postcode'])
    return ', '.join(parts) if parts else ''


def classify_facility_type(props: dict) -> str:
    """Classify facility into standard types."""
    amenity = props.get('amenity', '').lower()
    healthcare = props.get('healthcare', '').lower()
    
    # Check amenity first
    if amenity in FACILITY_TYPES:
        return FACILITY_TYPES[amenity]
    
    # Check healthcare tag
    if healthcare in FACILITY_TYPES:
        return FACILITY_TYPES[healthcare]
    
    # Default based on keywords
    if 'hospital' in amenity or 'hospital' in healthcare:
        return 'hospital'
    if 'clinic' in amenity or 'clinic' in healthcare:
        return 'clinic'
    if 'pharmacy' in amenity or 'pharmacy' in healthcare:
        return 'pharmacy'
    
    return 'other'


def has_emergency(props: dict) -> bool:
    """Check if facility has emergency services."""
    emergency = props.get('emergency', '').lower()
    return emergency == 'yes' or emergency == 'true'


def has_specialists(props: dict) -> bool:
    """Check if facility has specialist services."""
    specialty = props.get('healthcare:speciality', '')
    return bool(specialty and specialty.strip())


def extract_services(props: dict) -> list:
    """Extract list of services offered."""
    services = []
    
    specialty = props.get('healthcare:speciality', '')
    if specialty:
        services.extend([s.strip() for s in specialty.split(';')])
    
    if has_emergency(props):
        services.append('emergency')
    
    amenity = props.get('amenity', '')
    if amenity:
        services.append(amenity)
    
    return list(set(services))


def process_features(features: list) -> list:
    """Process all GeoJSON features into facility records."""
    facilities = []
    skipped = {'no_coords': 0, 'non_alaska': 0, 'unknown_type': 0}
    
    for feature in features:
        props = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        
        # Get coordinates
        lat, lon = get_centroid(geometry)
        if lat is None or lon is None:
            skipped['no_coords'] += 1
            continue
        
        # Filter to Alaska region (lat: 51-72, lon: -180 to -129)
        # Also include some margin for edge cases
        if not (50 <= lat <= 73 and -180 <= lon <= -128):
            skipped['non_alaska'] += 1
            continue
        
        # Get facility type
        facility_type = classify_facility_type(props)
        if facility_type == 'other':
            skipped['unknown_type'] += 1
            continue
        
        # Build facility record
        facility = {
            'osm_id': props.get('@id', feature.get('id', '')),
            'name': props.get('name', 'Unknown Facility'),
            'facility_type': facility_type,
            'latitude': round(lat, 6),
            'longitude': round(lon, 6),
            'address': parse_address(props),
            'phone': props.get('phone', ''),
            'website': props.get('website', ''),
            'has_emergency': has_emergency(props),
            'has_specialists': has_specialists(props),
            'services': ';'.join(extract_services(props)),
            'beds': props.get('beds', ''),
            'opening_hours': props.get('opening_hours', ''),
            'wheelchair': props.get('wheelchair', ''),
            'operator': props.get('operator', '')
        }
        
        facilities.append(facility)
    
    print(f"Processed {len(facilities)} facilities")
    print(f"   Skipped: {skipped}")
    return facilities


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two points using Haversine formula."""
    R = 6371  # Earth's radius in km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def generate_summary(facilities: list) -> dict:
    """Generate summary statistics."""
    by_type: dict = {}
    summary: dict = {
        'total_facilities': len(facilities),
        'with_emergency': 0,
        'with_specialists': 0,
        'with_phone': 0,
        'with_website': 0
    }
    
    for f in facilities:
        # Count by type
        ftype = f['facility_type']
        by_type[ftype] = by_type.get(ftype, 0) + 1
        
        # Count features
        if f['has_emergency']:
            summary['with_emergency'] += 1
        if f['has_specialists']:
            summary['with_specialists'] += 1
        if f['phone']:
            summary['with_phone'] += 1
        if f['website']:
            summary['with_website'] += 1
            
    summary['by_type'] = by_type
    return summary


def save_csv(facilities: list, filepath: str):
    """Save facilities to CSV."""
    import csv
    
    if not facilities:
        print("No facilities to save!")
        return
    
    fieldnames = list(facilities[0].keys())
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(facilities)
    
    print(f"Saved {len(facilities)} facilities to: {filepath}")


def save_summary(summary: dict, filepath: str):
    """Save summary to CSV."""
    import csv
    
    rows = [
        {'metric': 'total_facilities', 'value': summary['total_facilities']},
        {'metric': 'with_emergency', 'value': summary['with_emergency']},
        {'metric': 'with_specialists', 'value': summary['with_specialists']},
        {'metric': 'with_phone', 'value': summary['with_phone']},
        {'metric': 'with_website', 'value': summary['with_website']}
    ]
    
    for ftype, count in summary['by_type'].items():
        rows.append({'metric': f'type_{ftype}', 'value': count})
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['metric', 'value'])
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Saved summary to: {filepath}")


def print_report(summary: dict):
    """Print summary report."""
    print("\n" + "="*60)
    print("HEALTHCARE FACILITIES SUMMARY REPORT")
    print("="*60)
    
    print(f"\nTotal Facilities: {summary['total_facilities']}")
    
    print("\nBy Type:")
    for ftype, count in sorted(summary['by_type'].items(), key=lambda x: -x[1]):
        pct = count / summary['total_facilities'] * 100
        print(f"   {ftype}: {count} ({pct:.1f}%)")
    
    print("\nFeatures:")
    print(f"   Emergency services: {summary['with_emergency']}")
    print(f"   Specialist services: {summary['with_specialists']}")
    print(f"   Has phone number: {summary['with_phone']}")
    print(f"   Has website: {summary['with_website']}")
    print("="*60 + "\n")


def main():
    """Main preprocessing pipeline."""
    print("\n" + "="*60)
    print("HEALTHCARE FACILITY DATA PREPROCESSING")
    print("="*60 + "\n")
    
    # Define paths
    script_dir = Path(__file__).parent
    raw_data_path = script_dir.parent / 'raw' / 'alaska_healthsites.geojson'
    output_dir = script_dir.parent / 'processed_data'
    
    # Check if input file exists
    if not raw_data_path.exists():
        print(f"Error: Input file not found at {raw_data_path}")
        return
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Load GeoJSON
    data = load_geojson(str(raw_data_path))
    
    # Step 2: Process features
    facilities = process_features(data.get('features', []))
    
    # Step 3: Generate summary
    summary = generate_summary(facilities)
    
    # Step 4: Print report
    print_report(summary)
    
    # Step 5: Save outputs
    save_csv(facilities, str(output_dir / 'healthcare_facilities.csv'))
    save_summary(summary, str(output_dir / 'healthcare_summary.csv'))
    
    print("Preprocessing complete!\n")
    
    return facilities, summary


if __name__ == '__main__':
    main()
