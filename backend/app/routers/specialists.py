from fastapi import APIRouter, Query
from app.services.specialists_service import fetch_specialists

router = APIRouter()

@router.get("/")
def get_specialists(
    taxonomy: str = Query(None, description="Specialty name or taxonomy code"),
    state: str = Query(None, description="State abbreviation, e.g., AK"),
    city: str = Query(None, description="City name")
):
    return fetch_specialists(taxonomy=taxonomy, state=state, city=city)
