import math
from .regions_service import generate_alaska_grid

def physical_desert_score(items):
    n = len(items)
    if n == 0:
        return 1.0
    return round(max(0.0, 1 - math.log(n + 1) /3), 3)


def telehealth_desert_score(items, broadband):
    n = len(items)

    if n == 0 and broadband["overall"] == 0:
        return 1.0
    internet_penalty = 1 - broadband["overall"]

    provider_bonus = min(math.log(n + 1) / 2, 1)

    score = internet_penalty * (1 - provider_bonus)

    return round(min(max(score, 0), 1), 3)


def region_broadband_metrics(region, h3_broadband_map):
    h3 = region.get("h3")

    if not h3 or h3 not in h3_broadband_map:
        return {
            "fiber": 0,
            "cable": 0,
            "licensed_fixed_wireless": 0,
            "copper": 0,
            "overall": 0.0
        }

    techs = h3_broadband_map[h3]

    overall = max(techs.values()) if techs else 0.0

    return {
        **techs,
        "overall": round(overall, 3)
    }

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))
def assign_items_to_regions(regions, items, care_mode, radius_km=50):

    for region in regions:
        rlat = region["center"]["lat"]
        rlon = region["center"]["lon"]

        for item in items:
            ilat = item["location"]["lat"]
            ilon = item["location"]["lon"]

            if haversine(rlat, rlon, ilat, ilon) <= radius_km:
                region[f"{care_mode}_items"].append(item)

def compute_desert_index(
    specialists,
    healthsites,
    h3_broadband_map
):
    regions = generate_alaska_grid(step=0.5)

    physical_specs = [s for s in specialists if "physical" in s["care_mode"] ]
    tele_specs = [s for s in specialists if "telehealth" in s["care_mode"] ]

    physical_items = physical_specs + healthsites

    assign_items_to_regions(regions, physical_items, "physical")
    assign_items_to_regions(regions, tele_specs, "telehealth")

    results = []
    for r in regions:
        broadband = region_broadband_metrics(r, h3_broadband_map)
        results.append({
            "center": r["center"],
            "physical_desert": physical_desert_score(r["physical_items"]),
            "telehealth_desert": telehealth_desert_score(
                r["telehealth_items"],
                broadband
            ),
            "physical_count": len(r["physical_items"]),
            "telehealth_count": len(r["telehealth_items"])
        })

    return results
