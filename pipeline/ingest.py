import os
import time
import requests
import json

HEALTHSITES_API_URL = "https://healthsites.io/api/v3/facilities/"
ALASKA_EXTENT = "-179.1489,51.2142,-129.9795,71.3651"
API_KEY = os.getenv("HEALTHSITES_API_KEY", "PLACEHOLDER_KEY")

def fetch_healthsites_page(page=1, country="AK"):
    """
    Fetches a single page of healthcare facilities from healthsites.io.
    """
    params = {
        "api-key": API_KEY,
        "page": page,
        "country": country,
        "extent": ALASKA_EXTENT,
        "output": "json"
    }
    
    try:
        response = requests.get(HEALTHSITES_API_URL, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching page {page}: {e}")
        return None

def normalize_facility(facility):
    """
    Normalizes a single healthsite facility record into a GeoJSON Feature.
    """
    # The API structure can vary based on tag-format, assuming standard OSM-like tags.
    attributes = facility.get("attributes", {})
    name = attributes.get("name") or facility.get("name") or "Unnamed Facility"
    f_type = attributes.get("amenity") or attributes.get("healthcare") or "Unknown"
    
    # Coordinates are typically in [lon, lat] for GeoJSON
    lon = facility.get("centroid", {}).get("coordinates", [0, 0])[0]
    lat = facility.get("centroid", {}).get("coordinates", [0, 0])[1]
    
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat]
        },
        "properties": {
            "name": name,
            "type": f_type,
            "source": "healthsites.io",
            "id": facility.get("uuid"),
            "last_update": facility.get("upstream_updated")
        }
    }
    return feature

def main():
    data_dir = os.getenv("DATA_DIR", "data")
    raw_dir = os.path.join(data_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    
    output_file = os.path.join(raw_dir, "alaska_healthsites.geojson")
    
    all_features = []
    page = 1
    
    print(f"Starting ingestion from healthsites.io for Alaska (country=AK)...")
    
    while True:
        print(f"Fetching page {page}...")
        data = fetch_healthsites_page(page=page)
        
        if not data or len(data) == 0:
            print("No more data or error reached.")
            break
        
        for item in data:
            feature = normalize_facility(item)
            all_features.append(feature)
        
        # Simple pagination check: if we got a full page (usually 100), try next.
        # Healthsites API V3 docs are sparse on total count, so we loop until empty.
        if len(data) < 1: # Adjust if API returns empty list or smaller than page size
            break
            
        page += 1
        # Respect rate limits (healthsites.io usually allows 1 req/sec or similar)
        time.sleep(1) 
        
        # Safety break for demo purposes (optional)
        if page > 10: 
            break

    geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "name": "Alaska Healthcare Facilities",
            "source": "healthsites.io",
            "bbox": ALASKA_EXTENT,
            "count": len(all_features)
        },
        "features": all_features
    }
    
    with open(output_file, "w") as f:
        json.dump(geojson, f, indent=2)
        
    print(f"Ingestion complete. {len(all_features)} facilities saved to {output_file}.")

if __name__ == "__main__":
    main()
