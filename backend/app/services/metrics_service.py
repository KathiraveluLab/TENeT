from .healthsites_service import fetch_healthsites
from .specialists_service import fetch_specialists
from .transport_service import get_transport_score
import requests
from opencage.geocoder import OpenCageGeocode
import os

OPENCAGE_API_KEY = os.getenv("OPENCAGE_API_KEY")
geocoder = OpenCageGeocode(OPENCAGE_API_KEY)

def geocode(address: str):
    if not address:
        return None

    try:
        result = geocoder.geocode(address, limit=1)
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None

    if not result:
        return None
    
    lat = result[0]["geometry"]["lat"]
    lon = result[0]["geometry"]["lng"]
    return lat, lon


def compute_desert_index(state="AK"):
    healthsites = fetch_healthsites(state)["data"]
    specialists = fetch_specialists("cardiology", state)["data"]  # Example
    scores = []

    for site in healthsites:
        addr = site["practice_address"]
        if not addr or not addr["address"]:
            continue

        full_addr = f"{addr.get('address', '')} {addr.get('city', '')} {addr.get('state', '')}".strip()
        latlon = geocode(full_addr)

        if latlon:
            lat, lon = latlon
            transport = get_transport_score(lat, lon)
        else:
            transport = None
 
        scores.append({
            "npi": site["npi"],
            "name": site["name"],
            "taxonomies": site["taxonomies"],
            "transport_score": transport.get("transport_score") if transport else None,
            "is_specialist": any("cardio" in (t.get("desc") or "").lower() for t in site["taxonomies"])
        })

    return {
        "count": len(scores),
        "data": scores
    }
