from fastapi import APIRouter
from app.services.specialists_service import fetch_specialists
from app.services.healthsites_service import fetch_healthsites
from app.services.metrics_service import compute_community_desert_index
from app.services.broadband_service import load_broadband_by_h3,load_actual_broadband_by_h3
from app.services.communities import load_communities
router = APIRouter(tags=["metrics"])
from app.services.broadband_service import DATA_DIR, BROADBAND_SOURCES

@router.get("/desert-index")
def desert_index():
    communities_gdf = load_communities()
    specialists = fetch_specialists()["data"]
    healthsites = fetch_healthsites()["data"]

    h3_broadband_map = load_broadband_by_h3(
    [(DATA_DIR / fname, tech) for fname, tech in BROADBAND_SOURCES]
)
    h3_actual_map = load_actual_broadband_by_h3()
    return compute_community_desert_index(
        communities_gdf,
        specialists,
        healthsites,
        h3_broadband_map,
        h3_actual_map
    )
