#!/usr/bin/env python3
"""
Update community coordinates using USGS GNIS (Geographic Names Information System).
Downloads official Alaska place names with accurate coordinates.

Usage:
    python fix_coordinates_gnis.py
"""

import os
import csv
import requests
import zipfile
import io

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'processed_data')
INPUT_FILE = os.path.join(DATA_DIR, 'clean_transport_profiles_1.csv')
OUTPUT_FILE = os.path.join(DATA_DIR, 'clean_transport_profiles_fixed.csv')

# GNIS data URL for Alaska
GNIS_URL = "https://geonames.usgs.gov/docs/stategaz/AK_Features.zip"


def download_gnis_data():
    """Download and extract GNIS Alaska data."""
    print("📥 Downloading GNIS Alaska data...")
    
    response = requests.get(GNIS_URL, timeout=60)
    response.raise_for_status()
    
    # Extract from zip
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        # Find the text file in the zip
        for name in z.namelist():
            if name.endswith('.txt'):
                print(f"  Extracting {name}...")
                content = z.read(name).decode('utf-8', errors='replace')
                return content
    
    raise Exception("No .txt file found in GNIS zip")


def parse_gnis_data(content: str) -> dict:
    """Parse GNIS data into a dictionary of place -> (lat, lon)."""
    places = {}
    
    lines = content.strip().split('\n')
    headers = lines[0].split('|')
    
    # Find column indices
    try:
        name_idx = headers.index('FEATURE_NAME')
        class_idx = headers.index('FEATURE_CLASS')
        lat_idx = headers.index('PRIM_LAT_DEC')
        lon_idx = headers.index('PRIM_LONG_DEC')
    except ValueError as e:
        print(f"  Header error: {e}")
        print(f"  Headers: {headers[:10]}...")
        return places
    
    for line in lines[1:]:
        parts = line.split('|')
        if len(parts) <= max(name_idx, class_idx, lat_idx, lon_idx):
            continue
        
        name = parts[name_idx].strip()
        feature_class = parts[class_idx].strip()
        
        # Only include populated places, locales, and census areas
        if feature_class not in ['Populated Place', 'Census', 'Locale', 'Civil']:
            continue
        
        try:
            lat = float(parts[lat_idx])
            lon = float(parts[lon_idx])
            
            # Store with lowercase name for matching
            key = name.lower().replace(' ', '_')
            places[key] = (lat, lon, name, feature_class)
            
            # Also store without underscores
            key2 = name.lower()
            if key2 not in places:
                places[key2] = (lat, lon, name, feature_class)
                
        except (ValueError, IndexError):
            continue
    
    return places


def main():
    print("=" * 60)
    print("GNIS COORDINATE FIXER")
    print("=" * 60)
    
    # Download GNIS data
    try:
        content = download_gnis_data()
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        return
    
    # Parse GNIS data
    print("\n📊 Parsing GNIS data...")
    gnis_places = parse_gnis_data(content)
    print(f"  Found {len(gnis_places)} Alaska places")
    
    # Read input CSV
    print(f"\n📄 Reading {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    print(f"  Found {len(rows)} communities")
    
    # Update coordinates
    print("\n🔄 Updating coordinates...")
    updated = 0
    not_found = []
    
    for row in rows:
        community = row['community'].lower()
        old_lat = float(row['latitude'])
        old_lon = float(row['longitude'])
        
        # Try different name variations
        match = None
        for key in [community, community.replace('_', ' '), community.replace(' ', '_')]:
            if key in gnis_places:
                match = gnis_places[key]
                break
        
        if match:
            new_lat, new_lon, official_name, feature_class = match
            
            # Check if significantly different (more than 0.01 degrees = ~1km)
            if abs(old_lat - new_lat) > 0.01 or abs(old_lon - new_lon) > 0.01:
                print(f"  {community}: ({old_lat:.4f}, {old_lon:.4f}) → ({new_lat:.4f}, {new_lon:.4f})")
                row['latitude'] = round(new_lat, 6)
                row['longitude'] = round(new_lon, 6)
                updated += 1
        else:
            not_found.append(community)
    
    # Write output
    print(f"\n📝 Writing {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total communities: {len(rows)}")
    print(f"  Coordinates updated: {updated}")
    print(f"  Not found in GNIS: {len(not_found)}")
    
    if not_found and len(not_found) <= 30:
        print(f"\n  Not found ({len(not_found)}):")
        for name in not_found[:30]:
            print(f"    - {name}")
    
    print(f"\n[SUCCESS] Output saved to: {OUTPUT_FILE}")
    print("\nTo apply changes, run:")
    print(f"  cp {OUTPUT_FILE} {INPUT_FILE}")


if __name__ == "__main__":
    main()
