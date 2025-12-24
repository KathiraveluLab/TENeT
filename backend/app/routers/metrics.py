from fastapi import APIRouter
from app.services.specialists_service import fetch_specialists
from app.services.healthsites_service import fetch_healthsites
from app.services.metrics_service import compute_desert_index
from app.services.broadband_service import load_broadband_by_h3
router = APIRouter(tags=["metrics"])


@router.get("/desert-index")
def desert_index():
    specialists = fetch_specialists()["data"]
    healthsites = fetch_healthsites()["data"]

    h3_broadband_map = load_broadband_by_h3([
        ("app/data/bdc_02_FibertothePremises_fixed_broadband_J25_09dec2025.csv", "fiber"),
        ("app/data/bdc_02_Cable_fixed_broadband_J25_09dec2025.csv", "cable"),
        ("app/data/bdc_02_LicensedFixedWireless_fixed_broadband_J25_09dec2025.csv", "licensed_fixed_wireless"),
        ("app/data/bdc_02_Copper_fixed_broadband_J25_09dec2025.csv", "copper"),
    ])

    return compute_desert_index(
        specialists,
        healthsites,
        h3_broadband_map
    )
