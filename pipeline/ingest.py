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
    
    # Check if API_KEY is valid or set to placeholder
    if API_KEY != "PLACEHOLDER_KEY":
        print(f"Starting ingestion from healthsites.io for Alaska (country=AK)...")
        page = 1
        while True:
            print(f"Fetching page {page}...")
            data = fetch_healthsites_page(page=page)
            
            if not data or len(data) == 0:
                print("No more data or error reached.")
                break
            
            for item in data:
                feature = normalize_facility(item)
                all_features.append(feature)
            
            # Simple pagination check (V3 usually returns ~100 per page)
            if len(data) < 1: 
                break
            page += 1
            time.sleep(1) # Respect rate limits
            if page > 10: break
    else:
        print("Using mock data for testing (HEALTHSITES_API_KEY missing)...")
        # Mock data for demonstration if no API key is provided
        mock_data = [
            {"centroid": {"coordinates": [-149.9003, 61.2181]}, "attributes": {"name": "Anchorage Medical Center", "amenity": "hospital"}},
            {"centroid": {"coordinates": [-147.7164, 64.8378]}, "attributes": {"name": "Fairbanks Clinic", "amenity": "clinic"}},
            {"centroid": {"coordinates": [-165.4064, 64.5011]}, "attributes": {"name": "Nome Community Clinic", "amenity": "clinic"}},
            {"centroid": {"coordinates": [-134.4197, 58.3019]}, "attributes": {"name": "Juneau Health Center", "amenity": "doctor"}}
        ]
        for item in mock_data:
            all_features.append(normalize_facility(item))

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
