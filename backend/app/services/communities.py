import geopandas as gpd
import pandas as pd
from pathlib import Path
import h3
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
H3_RESOLUTION = 8

def load_communities():
    places = gpd.read_file(
        DATA_DIR / "tl_2025_02_place" / "tl_2025_02_place.shp"
    )
    anvsa = gpd.read_file(
        DATA_DIR / "tl_2025_us_aiannh" / "tl_2025_us_aiannh.shp"
    )

    places = places[["GEOID", "NAME", "geometry"]].copy()
    places["type"] = "place"

    anvsa = anvsa[["GEOID", "NAME", "geometry"]].copy()
    anvsa["type"] = "native_village"

    gdf = gpd.GeoDataFrame(
        pd.concat([places, anvsa], ignore_index=True),
        crs=places.crs
    )
    gdf_proj = gdf.to_crs(epsg=5070)
    gdf_proj["centroid"] = gdf_proj.geometry.centroid

    # Convert centroids back to lat/lon
    centroids = gdf_proj["centroid"].to_crs(epsg=4326)

    gdf = gdf.to_crs(epsg=4326)
    gdf["lat"] = centroids.y
    gdf["lon"] = centroids.x
    gdf["h3"] = gdf.apply(
    lambda r: h3.latlng_to_cell(r["lat"], r["lon"], H3_RESOLUTION),
    axis=1
)

    return gdf
