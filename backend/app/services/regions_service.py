from pathlib import Path
import json
from shapely.geometry import Point, shape
import h3
with open(Path(__file__).resolve().parent.parent / "data" / "alaska_boundary.geojson") as f:
    alaska_geojson = json.load(f)

alaska_geom = shape(alaska_geojson["features"][0]["geometry"])

def generate_alaska_grid(step=0.5):
    min_lat, max_lat = 51.2, 71.5
    min_lon, max_lon = -179.0, -129.9

    cells = []
    lat = min_lat
    while lat <= max_lat:
        lon = min_lon
        while lon <= max_lon:
            p = Point(lon, lat)
            if alaska_geom.intersects(p):
                h3_id = h3.latlng_to_cell(lat, lon, 8) 

                cells.append({
                    "center": {"lat": lat, "lon": lon},
                    "h3": h3_id,
                    "physical_items": [],
                    "telehealth_items": []
                })
            lon += step
        lat += step

    return cells
