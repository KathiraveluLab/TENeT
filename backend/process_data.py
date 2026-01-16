import pandas as pd
import geopandas as gpd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

tracts = gpd.read_file(BASE_DIR / "data" / "alaska_tracts.geojson")
tracts["tract_geoid"] = tracts["GEOID"]

bb = pd.read_csv(BASE_DIR / "data" / "broadband.csv")
bb = bb[
    [
        "block_geoid",
        "max_advertised_download_speed",
        "max_advertised_upload_speed",
        "low_latency"
    ]
]

bb["tract_geoid"] = bb["block_geoid"].astype(str).str[:11]

bb_agg = (
    bb.groupby("tract_geoid")
    .agg(
        avg_download=("max_advertised_download_speed", "mean"),
        avg_upload=("max_advertised_upload_speed", "mean"),
        low_latency_ratio=("low_latency", "mean")
    )
    .reset_index()
)


health = pd.read_csv(BASE_DIR / "data" / "healthsite.csv")
health = health[["lat", "lon", "healthcare", "amenity"]]
health["facility_type"] = health["healthcare"].fillna(health["amenity"])

health_gdf = gpd.GeoDataFrame(
    health,
    geometry=gpd.points_from_xy(health["lon"], health["lat"]),
    crs="EPSG:4326"
).to_crs(tracts.crs)

health_join = gpd.sjoin(
    health_gdf,
    tracts[["tract_geoid", "geometry"]],
    predicate="within"
)

clinic_count = (
    health_join.groupby("tract_geoid")
    .size()
    .reset_index(name="clinic_count")
)

final = (
    tracts
    .merge(bb_agg, on="tract_geoid", how="left")
    .merge(clinic_count, on="tract_geoid", how="left")
).fillna(0)


final["healthcare_score"] = 1 / (1 + final["clinic_count"])
final["internet_score"] = (
    final["avg_download"]
    + 0.5 * final["avg_upload"]
    + 10 * final["low_latency_ratio"]
)

def mark_zone(row):
    if row["healthcare_score"] >= 0.6 and row["internet_score"] >= 50:
        return "HIGH"
    elif row["healthcare_score"] >= 0.6 and row["internet_score"] >= 25:
        return "MEDIUM"
    else:
        return "LOW"

final["zone"] = final.apply(mark_zone, axis=1)


OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

final.to_file(OUTPUT_DIR / "alaska_telehealth.geojson", driver="GeoJSON")

print("alaska_telehealth.geojson generated successfully")
