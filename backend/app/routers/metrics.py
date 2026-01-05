from fastapi import APIRouter
from app.services.specialists_service import fetch_specialists
from app.services.healthsites_service import fetch_healthsites
from app.services.metrics_service import compute_desert_index
from app.services.broadband_service import load_broadband_by_h3
router = APIRouter(tags=["metrics"])
from app.services.broadband_service import DATA_DIR, BROADBAND_SOURCES

@router.get("/desert-index")
def desert_index():
    specialists = fetch_specialists()["data"]
    healthsites = fetch_healthsites()["data"]

    h3_broadband_map = load_broadband_by_h3(
    [(DATA_DIR / fname, tech) for fname, tech in BROADBAND_SOURCES]
)

    return compute_desert_index(
        specialists,
        healthsites,
        h3_broadband_map
    )
