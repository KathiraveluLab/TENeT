import pandas as pd
import geopandas as gpd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

df = pd.read_csv(BASE / "data" / "healthsite.csv")
df = df.dropna(subset=["lat", "lon"])

gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["lon"], df["lat"]),
    crs="EPSG:4326"
)

out = BASE / "frontend" / "clinics.geojson"
gdf.to_file(out, driver="GeoJSON")

print("clinics.geojson created")
