from fastapi import APIRouter
from app.services.transport_service import get_transport_score

router = APIRouter()

@router.get("/")
def transport_score(lat: float, lon: float):
    return get_transport_score(lat,lon)
