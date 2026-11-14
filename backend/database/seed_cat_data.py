"""
Seed database with CAT data from preprocessed CSV.
Loads Alaska community transport profiles into CATRegion and CATDataPoint tables.
"""
import csv
import json
import math
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import SessionLocal
from database.models import CATRegion, CATDataPoint, CATUpload


def _point_in_ring(lon: float, lat: float, ring) -> bool:
    """Ray-casting test for a GeoJSON polygon ring."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside


def _load_alaska_boroughs():
    """Load Alaska Borough/Census Area polygons and centroids for region labeling."""
    geojson_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'data', 'raw', 'Alaska_Borough_and_Census_Area_Boundaries.geojson'
    )
    if not os.path.exists(geojson_path):
        return []

    with open(geojson_path, 'r', encoding='utf-8') as handle:
        data = json.load(handle)

    boroughs = []
    for feature in data.get('features', []):
        props = feature.get('properties') or {}
        geometry = feature.get('geometry') or {}
        coords = geometry.get('coordinates') or []
        polygons = coords if geometry.get('type') == 'MultiPolygon' else [coords]
        all_pts = [pt for poly in polygons if poly for pt in poly[0]]
        if not all_pts:
            continue
        centroid_lon = sum(pt[0] for pt in all_pts) / len(all_pts)
        centroid_lat = sum(pt[1] for pt in all_pts) / len(all_pts)
        boroughs.append({
            'economic_region': props.get('EconomicRegion'),
            'community_name': props.get('CommunityName'),
            'polygons': polygons,
            'centroid_lat': centroid_lat,
            'centroid_lon': centroid_lon,
        })
    return boroughs


def _resolve_alaska_region(lat: float, lon: float, boroughs: list) -> tuple[str | None, str | None]:
    """Return (EconomicRegion, Borough/Census Area) for a community coordinate."""
    for borough in boroughs:
        for poly in borough['polygons']:
            if not poly:
                continue
            if _point_in_ring(lon, lat, poly[0]) and not any(
                _point_in_ring(lon, lat, hole) for hole in poly[1:]
            ):
                return borough['economic_region'], borough['community_name']

    if not boroughs:
        return None, None

    nearest = min(
        boroughs,
        key=lambda b: math.hypot(lat - b['centroid_lat'], (lon - b['centroid_lon']) * 0.5),
    )
    return nearest['economic_region'], nearest['community_name']


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

    boroughs = _load_alaska_boroughs()
    db = SessionLocal()
    regions_created = 0
    data_points_created = 0

    try:
        db.query(CATDataPoint).delete()
        db.query(CATUpload).delete()
        db.commit()

        # First, create a seed upload record
        seed_upload = CATUpload(
            filename=os.path.basename(csv_path),
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
                economic_region, borough_name = _resolve_alaska_region(latitude, longitude, boroughs)
                region_properties = {
                    'region': economic_region or 'unknown',
                    'economic_region': economic_region or 'unknown',
                    'borough': borough_name,
                    'tier_justification': row.get('tier_justification', ''),
                    'primary_access_modes': row.get('primary_access_modes', ''),
                    'has_airport': row.get('has_airport', 'False').lower() == 'true',
                    'has_road_access': row.get('has_road_access', 'False').lower() == 'true',
                    'has_water_access': row.get('has_water_access', 'False').lower() == 'true',
                    'coastal': row.get('coastal', 'False').lower() == 'true',
                }

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
                    region.properties = region_properties
                else:
                    region = CATRegion(
                        region_code=region_code,
                        region_name=community.title(),
                        tier_level=cat_tier,
                        centroid_lat=latitude,
                        centroid_lon=longitude,
                        access_score=access_score,
                        properties=region_properties,
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
