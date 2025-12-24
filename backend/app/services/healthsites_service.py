import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

def load_healthsites():
    with open(DATA_DIR / "healthsites_alaska.geojson") as f:
        return json.load(f)["features"]


def fetch_healthsites():
    raw = load_healthsites()
    sites = []

    for feature in raw:
        props = feature["properties"]
        geom = feature["geometry"]

        sites.append({
            "id": props.get("id"),
            "name": props.get("name"),
            "amenity": props.get("amenity"),
            "healthcare": props.get("healthcare"),
            "care_mode": "physical",
            "location": {
                "lat": geom["coordinates"][1],
                "lon": geom["coordinates"][0],
            }
        })

    return {
        "count": len(sites),
        "data": sites
    }
