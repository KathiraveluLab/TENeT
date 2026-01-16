import math
#from .regions_service import generate_alaska_grid
from .communities_scoring_service import items_to_gdf,assign_items_to_communities,group_items_by_community
import pandas as pd

PHYSICAL_SCORE_LOG_DIVISOR = 3
HIGH = 0.6
LOW = 0.3
GAP_HIGH = 0.3

def physical_desert_score(items):
    n = len(items)
    if n == 0:
        return 1.0
    return round(max(0.0, 1 - math.log(n + 1) / PHYSICAL_SCORE_LOG_DIVISOR), 3)

TELEHEALTH_PROVIDER_DIVISOR = 2
def telehealth_desert_score(items, broadband):
    n = len(items)

    if n == 0 and broadband["actual"] == 0:
        return 1.0
    internet_penalty = 1 - broadband["actual"]

    provider_bonus = min(math.log(n + 1) / TELEHEALTH_PROVIDER_DIVISOR, 1)

    score = internet_penalty * (1 - provider_bonus)

    return round(min(max(score, 0), 1), 3)

def broadband_for_community(
    c_h3,
    h3_advertised_map,
    h3_actual_map
):
    h3_id = c_h3

    # ---- Advertised (FCC / BDC) ----
    techs = h3_advertised_map.get(h3_id, {})
    advertised = max(techs.values()) if techs else 0.0
    advertised = round(advertised, 3)

    # ---- Actual (Ookla + RIPE) ----
    actual = round(h3_actual_map.get(h3_id, 0.0), 3)

    gap = round(max(advertised - actual, 0.0), 3)

    # ---- Service state (authoritative) ----
    if advertised >= HIGH and actual >= HIGH:
        state = "adequately_served"
        color = "#2E8B57"

    elif advertised <= LOW and actual <= LOW:
        state = "true_desert"
        color = "#8B0000"

    elif advertised >= HIGH and gap >= GAP_HIGH:
        state = "advertised_but_unreliable"
        color = "#E67E22"  

    else:
        state = "partially_served"
        color = "#F1C40F"

    return {
        "techs": techs,
        "advertised": advertised,
        "actual": actual,
        "gap": gap,
        "state": state,
        "color": color
    }


def compute_community_desert_index(
    communities_gdf,
    specialists,
    healthsites,
    h3_broadband_map,
    h3_actual_map
):
    spec_gdf = items_to_gdf(specialists)
    hs_gdf = items_to_gdf(healthsites)

    # Split by care mode
    physical_mask = spec_gdf["care_mode"].fillna("").str.contains(
    "physical", regex=False)
    physical_specs = spec_gdf.loc[physical_mask]

    tele_mask = spec_gdf["care_mode"].fillna("").str.contains(
    "telehealth", regex=False)
    tele_specs = spec_gdf.loc[tele_mask]


    # Spatial joins
    physical_join = assign_items_to_communities(
        communities_gdf,
        pd.concat([physical_specs, hs_gdf], ignore_index=True)
    )

    tele_join = assign_items_to_communities(
        communities_gdf,
        tele_specs
    )
    # Step 3: aggregation
    physical_map = group_items_by_community(physical_join)
    tele_map = group_items_by_community(tele_join)

    # Step 4: scoring
    features = []

    for _, c in communities_gdf.iterrows():
        geoid = c["GEOID"]

        physical_items = physical_map.get(geoid, [])
        tele_items = tele_map.get(geoid, [])
        broadband = broadband_for_community(c["h3"], h3_broadband_map, h3_actual_map)
        features.append({
            "type": "Feature",
            "geometry": c["geometry"].simplify(
            tolerance=0.001, preserve_topology=True).__geo_interface__,
            "properties": {
                "community": {
                    "name": c["NAME"],
                    "geoid": geoid,
                    "type": c.get("type", "place"),
                },
                "physical_desert": physical_desert_score(physical_items),
                "telehealth_desert": telehealth_desert_score(
                    tele_items, broadband
                ),
                "physical_count": len(physical_items),
                "telehealth_count": len(tele_items),
                "broadband": broadband,
            }
        })

    return {
    "type": "FeatureCollection",
    "features": features
    }