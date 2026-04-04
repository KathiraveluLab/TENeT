"""
Preprocess Transportation Data

Purpose:
- Load raw transportation datasets (air, road, water)
- Normalize schemas and community identifiers
- Collapse facilities into parent communities
- Reduce to signal-only transport features
- Produce one reliable transport profile per community
- Enrich with geographic, network, and healthcare placeholder data

This script is intentionally standalone and NOT coupled to TENeT yet.
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime
import math
from pyproj import Transformer

# Helpers
EXCLUDE_KEYWORDS = [
    "borough",
    "census",
    "area",
    "region",
    "alaska"
]


# Suffixes that indicate a facility row, not a standalone community
FACILITY_SUFFIXES = [
    " ferry",
    " dock",
    " terminal",
    " city",
    " village",
    " harbor",
    " port",
    " station",
    " airport",
]


# Non-human communities to exclude (military bases, industrial sites)
NON_COMMUNITY_EXCLUSIONS = [
    "joint base elmendorf-richardson",
    "red dog mine",
    "eielson afb",
    "usibelli",
]

# Non-residential or micro-local rows to drop entirely
NON_RESIDENTIAL_EXCLUSIONS = [
    "whitestone logging camp",
    "bill moore's slough",
    "pope-vannoy landing",
    "ptarmigan heights",
    "circle view stampede",
    "four mile road",
    "farm loop",
    "farmers loop",
    "northway junction",
]

# Explicit parent community mappings for sub-areas/neighborhoods
# Child rows will be merged into parent, then deleted
# Includes intermediate normalized forms to catch all variations
PARENT_COMMUNITY_MAP = {
    # Kodiak area
    "womens bay": "kodiak",
    "woody island": "kodiak",
    "port lions": "kodiak",
    # Ketchikan area
    "ward cove": "ketchikan",
    "ketchikan main": "ketchikan",
    "ketchikan main ferry": "ketchikan",
    # Juneau area
    "auke bay": "juneau",
    "auke bay ferry": "juneau",
    "auke bay east stern berth": "juneau",
    # Anchorage/road network area
    "bird creek": "anchorage",
    "diamond ridge": "homer",
    "willow creek": "willow",
    # Petersburg area
    "petersburg s mitkof": "petersburg",
    # Other merges
    "chignik dragnet": "chignik",
    "annette bay": "metlakatla",
    "annette bay ferry": "metlakatla",
    "clark bay": "cordova",
    "clark bay ferry": "cordova",
    "homer city": "homer",
    "tenakee": "tenakee springs",
    "tenakee city": "tenakee springs",
    # Old Harbor is a real community - consolidate dock naming variations
    "old harbor city": "old harbor",
}


FACILITY_KEYWORDS = [
    "dock",
    "terminal",
    "station",
    "airport",
    "harbor",
    "port",
    "village",
    "bay ferry",
]



def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )
    return df


def normalize_name(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.lower()
        .str.strip()
    )


def normalize_community_name(name: str) -> str:
    """
    Convert facility-level names into parent community names.
    Conservative rule-based stripping.
    """
    if not isinstance(name, str):
        return name

    name = str(name).lower().strip()
    
    for keyword in FACILITY_KEYWORDS:
        if keyword in name:  # type: ignore
            # Split only on the first occurrence for efficiency and correctness
            name = re.split(rf"\b{keyword}\b", name, 1)[0].strip()
            break
            
    return name


# Communities that should NOT have suffixes stripped (they are real community names)
PRESERVE_COMMUNITY_NAMES = [
    "old harbor",
    "cold bay",
    "tenakee springs",
]


def infer_parent(community: str) -> str:
    
    if not isinstance(community, str):
        return community
    
    community = community.strip()
    
    # Check explicit parent mapping first (with recursion for chained mappings)
    seen = set()
    while community in PARENT_COMMUNITY_MAP and community not in seen:
        seen.add(community)
        community = PARENT_COMMUNITY_MAP[community]
    
    # Skip suffix stripping for preserved community names
    if community in PRESERVE_COMMUNITY_NAMES:
        return community
    
    # Try suffix stripping
    original = str(community)
    for suffix in FACILITY_SUFFIXES:
        if str(community).endswith(str(suffix)):
            idx = int(len(str(suffix)))
            community = str(community)[:-idx].strip()  # type: ignore
            break
    
    # Check mapping again after suffix stripping
    while community in PARENT_COMMUNITY_MAP and community not in seen:
        seen.add(community)
        community = PARENT_COMMUNITY_MAP[community]
    
    return community


def inspect(df: pd.DataFrame, name: str):
    print(f"\n--- {name} ---")
    print("Shape:", df.shape)
    print("Columns:", df.columns.tolist())
    print(df.head(3))


# -----------------------------
# Coordinate conversion (Alaska Albers to WGS84)
# Using simplified inverse projection for Alaska Albers (EPSG:3338)
# Note: For production, use pyproj for accurate conversion
# -----------------------------

def alaska_albers_to_latlon(x, y):
    """
    Accurate conversion from Alaska Albers (EPSG:3338) to WGS84 using pyproj.
    """
    if pd.isna(x) or pd.isna(y):
        return np.nan, np.nan

    # Define transformer from Alaska Albers to WGS84
    # always_xy=True ensures (longitude, latitude) order for input and output
    transformer = Transformer.from_crs("EPSG:3338", "EPSG:4326", always_xy=True)

    # Transform coordinates
    lon, lat = transformer.transform(x, y)

    return float(f"{lat:.6f}"), float(f"{lon:.6f}")


# -----------------------------
# CAT Tier Classification Logic
# -----------------------------

def calculate_cat_tier(row):
    """
    Calculate Community Access Tier (CAT) based on transport modes.
    
    Tier 1: Full multimodal access (air + road + water OR air + road)
    Tier 2: Dual mode without road (air + water) 
    Tier 3: Single mode access (air only, road only, or water only)
    Tier 4: No direct scheduled access
    """
    modes = []
    if row.has_airport:
        modes.append("air")
    if row.has_road_access:
        modes.append("road")
    if row.has_water_access:
        modes.append("water")
    
    mode_count = len(modes)
    has_road = row.has_road_access
    
    if mode_count >= 2 and has_road:
        return 1  # Full multimodal with road
    elif mode_count >= 2:
        return 2  # Dual mode without road
    elif mode_count == 1:
        return 3  # Single mode
    else:
        return 4  # Isolated


def calculate_access_score(row):
    """
    Calculate access score (0-100) based on transport availability.
    
    Scoring:
    - Airport: +40 points
    - Road access: +35 points
    - Water access: +25 points
    """
    score = 0
    if row.has_airport:
        score += 40
    if row.has_road_access:
        score += 35
    if row.has_water_access:
        score += 25
    return score


def get_tier_justification(row):
    """Generate human-readable justification for CAT tier."""
    tier = row.cat_tier_level
    modes = row.primary_access_modes
    
    justifications = {
        1: f"Full multimodal access ({modes}) including road connectivity",
        2: f"Dual mode access ({modes}) without year-round road",
        3: f"Single mode access ({modes}) - limited transport options",
        4: "No direct scheduled access - requires charter or seasonal transport"
    }
    return justifications.get(tier, "Unknown tier")




# Load datasets
air_raw = pd.read_csv("../raw/Airways.csv", encoding="latin1")
road_raw = pd.read_csv("../raw/Roadways.csv", encoding="latin1")
water_raw = pd.read_csv("../raw/Waterways.csv", encoding="latin1")

air = normalize_columns(air_raw)
road = normalize_columns(road_raw)
water = normalize_columns(water_raw)

inspect(air, "AIRWAYS")
inspect(road, "ROADWAYS")
inspect(water, "WATERWAYS")



# Normalize community identifiers

air["community_raw"] = normalize_name(air["communityname"])
road["community_raw"] = normalize_name(road["communityname"])
water["community_raw"] = normalize_name(water["name"])

air["community"] = air["community_raw"].apply(normalize_community_name)
road["community"] = road["community_raw"].apply(normalize_community_name)
water["community"] = water["community_raw"].apply(normalize_community_name)

# Feature extraction
# AIR
air_clean = air[["community", "airport"]].copy()
air_clean["has_airport"] = air_clean["airport"].eq("Yes")
air_clean = air_clean[["community", "has_airport"]]

# ROAD - include additional fields
road_cols = ["community", "roadconnection"]
# Add coordinates if available
if "x" in road.columns or "ï»¿x" in road.columns:
    x_col = "x" if "x" in road.columns else "ï»¿x"
    road_cols.extend([x_col, "y"])
if "coastal" in road.columns:
    road_cols.append("coastal")
if "harbordock" in road.columns:
    road_cols.append("harbordock")
if "stateferry" in road.columns:
    road_cols.append("stateferry")
if "cargobarge" in road.columns:
    road_cols.append("cargobarge")

road_clean = road[road_cols].copy()
road_clean["has_road_access"] = road_clean["roadconnection"].eq("Yes")

# Rename x column if needed
if "ï»¿x" in road_clean.columns:
    road_clean = road_clean.rename(columns={"ï»¿x": "x"})

# Normalize coastal field
if "coastal" in road_clean.columns:
    road_clean["coastal"] = road_clean["coastal"].str.lower().eq("yes")
else:
    road_clean["coastal"] = False

# Normalize harbor/ferry/barge fields
for col in ["harbordock", "stateferry", "cargobarge"]:
    if col in road_clean.columns:
        road_clean[col] = road_clean[col].eq("Yes")
    else:
        road_clean[col] = False

# WATER - include lat/long if available
water_cols = ["community"]
if "lat_dd" in water.columns:
    water_cols.extend(["lat_dd", "long_dd"])
water_clean = water[water_cols].copy()
water_clean["has_water_access"] = True

# Merge & aggregate (community-level)

merged = (
    air_clean
    .merge(road_clean, on="community", how="outer")
    .merge(water_clean, on="community", how="outer")
)

transport_flags = [
    "has_airport",
    "has_road_access",
    "has_water_access"
]

merged[transport_flags] = merged[transport_flags].fillna(False)

# Fill additional boolean fields
for col in ["coastal", "harbordock", "stateferry", "cargobarge"]:
    if col in merged.columns:
        merged[col] = merged[col].fillna(False)

# Build aggregation dict
agg_dict = {
    "has_airport": "max",
    "has_road_access": "max",
    "has_water_access": "max"
}

# Add coordinate aggregation (take first non-null)
if "x" in merged.columns:
    agg_dict["x"] = "first"
    agg_dict["y"] = "first"
if "lat_dd" in merged.columns:
    agg_dict["lat_dd"] = "first"
    agg_dict["long_dd"] = "first"

# Add boolean field aggregation
for col in ["coastal", "harbordock", "stateferry", "cargobarge"]:
    if col in merged.columns:
        agg_dict[col] = "max"

# First aggregation: collapse by community name
community_level = (
    merged
    .groupby("community", as_index=False)
    .agg(agg_dict)
)

# Parent–child collapsing

# Map facility rows to parent communities
community_level["parent_community"] = community_level["community"].apply(infer_parent)

# Build parent aggregation dict
parent_agg_dict = {
    "has_airport": "max",
    "has_road_access": "max",
    "has_water_access": "max"
}

# Preserve coordinates and additional fields
for col in ["x", "y", "lat_dd", "long_dd"]:
    if col in community_level.columns:
        parent_agg_dict[col] = "first"

for col in ["coastal", "harbordock", "stateferry", "cargobarge"]:
    if col in community_level.columns:
        parent_agg_dict[col] = "max"

# Aggregate again by parent community (OR flags together)
community_level = (
    community_level
    .groupby("parent_community", as_index=False)
    .agg(parent_agg_dict)
)

# Rename parent_community back to community
community_level = community_level.rename(columns={"parent_community": "community"})

# Transport profile synthesis (AFTER aggregation)

def build_profile(row):
    """
    Build transport profile string from boolean flags.
    Must be called AFTER all aggregation is complete.
    """
    modes = []
    if row.has_airport:
        modes.append("air")
    if row.has_road_access:
        modes.append("road")
    if row.has_water_access:
        modes.append("water")
    return ",".join(modes) if modes else "isolated"


community_level["transport_profile"] = community_level.apply(
    build_profile, axis=1
)

community_level = community_level.sort_values("community")

# Output
print("\n--- FINAL TRANSPORT PROFILE SAMPLE ---")
print(community_level.head(10))

# Filter out non-community keywords (boroughs, census areas, etc.)
community_level = community_level[
    ~community_level["community"].str.contains(
        "|".join(EXCLUDE_KEYWORDS),
        regex=True
    )
]

# Filter out non-human communities (military bases, industrial sites)
community_level = community_level[
    ~community_level["community"].isin(NON_COMMUNITY_EXCLUSIONS)
]

# Filter out non-residential/micro-local rows
community_level = community_level[
    ~community_level["community"].isin(NON_RESIDENTIAL_EXCLUSIONS)
]

# Remove empty or null community names
community_level = community_level[
    community_level["community"].notna() &
    (community_level["community"].str.len() > 0)
]

# Rename columns for semantic clarity


community_level = community_level.rename(columns={
    "transport_profile": "primary_access_modes"
})

# Replace 'isolated' with 'no_direct_access' for clarity
community_level["primary_access_modes"] = community_level["primary_access_modes"].replace(
    "isolated", "no_direct_access"
)


# -----------------------------
# Add geographic coordinates
# -----------------------------

# Convert Alaska Albers X/Y to lat/lon if available
if "x" in community_level.columns and "y" in community_level.columns:
    coords = community_level.apply(
        lambda row: alaska_albers_to_latlon(row.get("x"), row.get("y")), 
        axis=1
    )
    community_level["latitude"] = coords.apply(lambda x: x[0])
    community_level["longitude"] = coords.apply(lambda x: x[1])
    
    # If we have precise lat/long from water data, prefer that
    if "lat_dd" in community_level.columns:
        mask = community_level["lat_dd"].notna()
        community_level.loc[mask, "latitude"] = community_level.loc[mask, "lat_dd"]
        community_level.loc[mask, "longitude"] = community_level.loc[mask, "long_dd"]
else:
    # Use water lat/long if no X/Y available
    if "lat_dd" in community_level.columns:
        community_level["latitude"] = community_level["lat_dd"]
        community_level["longitude"] = community_level["long_dd"]
    else:
        community_level["latitude"] = np.nan
        community_level["longitude"] = np.nan

# Round coordinates
community_level["latitude"] = community_level["latitude"].round(6)
community_level["longitude"] = community_level["longitude"].round(6)


# -----------------------------
# Add CAT Tier Classification
# -----------------------------

community_level["cat_tier_level"] = community_level.apply(calculate_cat_tier, axis=1)
community_level["access_score"] = community_level.apply(calculate_access_score, axis=1)
community_level["tier_justification"] = community_level.apply(get_tier_justification, axis=1)


# -----------------------------
# Temporal fields
# -----------------------------

community_level["data_collection_date"] = datetime.now().strftime("%Y-%m-%d")


# -----------------------------
# Final column ordering
# -----------------------------

# Define column order for output (only real data from source files)
output_columns = [
    # Identity
    "community",
    
    # Transport flags (from source data)
    "has_airport",
    "has_road_access", 
    "has_water_access",
    "primary_access_modes",
    
    # Geographic (from source data)
    "latitude",
    "longitude",
    "coastal",
    
    # CAT Classification (derived from transport flags)
    "cat_tier_level",
    "access_score",
    "tier_justification",
    
    # Additional transport details (from Roadways.csv)
    "harbordock",
    "stateferry",
    "cargobarge",
    
    # Temporal
    "data_collection_date",
]

# Only include columns that exist
output_columns = [col for col in output_columns if col in community_level.columns]
community_level = community_level[output_columns]


community_level.to_csv("../processed_data/clean_transport_profiles.csv", index=False)

print("\n✔ Preprocessing complete.")
print("✔ One row = one community")
print(f"✔ Total communities: {len(community_level)}")
print(f"✔ Columns: {len(community_level.columns)}")
print("✔ Output written to: clean_transport_profiles.csv")

# Show sample of output
print("\n--- OUTPUT SAMPLE ---")
sample_cols = ["community", "primary_access_modes", "latitude", "longitude", 
               "cat_tier_level", "access_score", "coastal"]
sample_cols = [c for c in sample_cols if c in community_level.columns]
print(community_level[sample_cols].head(10).to_string())
