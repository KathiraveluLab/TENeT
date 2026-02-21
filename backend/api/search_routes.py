"""
Search API Routes

City-level search using SQLite LIKE for autocomplete.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db, Community

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/communities/search/autocomplete")
async def autocomplete(
    q: str = Query("", description="Search term"),
    limit: int = Query(10, le=50, description="Max results"),
    db: Session = Depends(get_db),
):
    """
    Lightweight autocomplete endpoint for the search bar.

    Returns community_id, name, location, region.
    Uses SQLite LIKE for fast substring matching.
    """
    if not q.strip():
        return {"results": [], "count": 0}

    communities = (
        db.query(Community)
        .filter(Community.name.ilike(f"%{q}%"))
        .limit(limit)
        .all()
    )

    return {
        "results": [
            {
                "community_id": c.community_id,
                "name": c.name,
                "location": {"lat": c.latitude, "lon": c.longitude},
                "region": c.region,
                "population": c.population,
            }
            for c in communities
        ],
        "count": len(communities),
    }
