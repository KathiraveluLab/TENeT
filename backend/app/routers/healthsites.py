from fastapi import APIRouter, Query
from app.services.healthsites_service import fetch_healthsites

router = APIRouter()

@router.get("/")
def get_healthsites(state: str = "AK", city: str = None):
    return fetch_healthsites(state,city)