from .healthsites_service import fetch_healthsites
from .specialists_service import fetch_specialists
from .transport_service import get_transport_score
import math

def compute_desert_index(state="AK"):
    healthsites = fetch_healthsites(state)["data"]
    specialists = fetch_specialists("cardiology", state)["data"]  # Example
    scores = []

    for site in healthsites:
        addr = site["practice_address"]
        if not addr or not addr["address"]:
            continue

        # Can geocode these later
        lat, lon = None, None  

        transport = None
        if lat and lon:
            transport = get_transport_score(lat, lon)
        
        scores.append({
            "npi": site["npi"],
            "name": site["name"],
            "taxonomies": site["taxonomies"],
            "transport_score": transport["transport_score"] if transport else None,
            "is_specialist": any(t["desc"].lower().find("cardio") >= 0 for t in site["taxonomies"])
        })

    return {
        "count": len(scores),
        "data": scores
    }
