"""
Digital Equity API Routes

Extends the existing equity endpoints with:
  - Simulation / sensitivity analysis
  - Data coverage / transparency
  - Versioned responses
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db, Community
from core.simulation import simulate_all
from core.coverage import compute_coverage
from services.snapshot_service import generate_snapshot

router = APIRouter(prefix="/api", tags=["digital-equity-extended"])


# ── Simulation / Sensitivity Analysis ──────────────────────────────

@router.get("/simulate")
async def simulate(
    threshold: float = Query(2.0, description="Affordability threshold (% of income)"),
    radius: float = Query(5.0, description="Clinic search radius in km"),
    limit: int = Query(None, description="Limit communities processed"),
    db: Session = Depends(get_db),
):
    """
    Run sensitivity analysis with custom affordability and radius thresholds.

    Returns recalculated equity results **without** writing to the database.
    """
    return simulate_all(
        db,
        affordability_threshold=threshold,
        clinic_radius_km=radius,
        limit=limit,
    )


# ── Data Coverage / Transparency ──────────────────────────────────

@router.get("/system/coverage")
async def system_coverage(db: Session = Depends(get_db)):
    """
    Data transparency dashboard endpoint.

    Returns % of communities with income data, broadband data,
    clinic proximity, plus data timestamps.
    """
    return compute_coverage(db)


# ── Map Snapshot ──────────────────────────────────────────────────

@router.get("/snapshot")
async def snapshot(
    region: str = Query(None, description="Filter by region name"),
    width: int = Query(800, le=2000),
    height: int = Query(600, le=2000),
    zoom: int = Query(5, ge=3, le=12),
    db: Session = Depends(get_db),
):
    """
    Generate a static PNG map snapshot for embedding in reports.
    """
    communities = db.query(Community).all()
    png_bytes = generate_snapshot(
        communities,
        width=width,
        height=height,
        zoom=zoom,
        region=region,
    )
    media = "image/png" if png_bytes[:4] == b"\x89PNG" else "image/svg+xml"
    return Response(content=png_bytes, media_type=media)
