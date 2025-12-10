from fastapi import APIRouter
from app.services.metrics_service import compute_desert_index

router = APIRouter()

@router.get("/")
def desert_index(state: str = "AK"):
    return compute_desert_index(state)
