import json
from pathlib import Path
from .classifier import classify_specialist

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

def load_nppes():
    with open(DATA_DIR / "nppes_providers.geojson") as f:
        return json.load(f)["features"]
    
def fetch_specialists():
    raw = load_nppes()

    specialists = []

    for feature in raw:
        props = feature["properties"]
        geom = feature["geometry"]

        taxonomy = props.get("taxonomy", "")

        specialists.append({
            "npi": props.get("npi"),
            "name": props.get("name"),
            "taxonomy": taxonomy,
            "care_mode": classify_specialist(taxonomy),
            "location": {
                "lat": geom["coordinates"][1],
                "lon": geom["coordinates"][0],
            }
        })

    return {
        "count": len(specialists),
        "data": specialists
    }
