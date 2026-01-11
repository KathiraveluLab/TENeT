"""
API routes for community data endpoints.

All endpoints are read-only and return raw data values.
Enhanced with season-aware analysis and healthcare necessity scoring.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import (
    CommunityRecord, CommunityListItem, HealthcareData, ConnectivityData
)
from app.data_store import data_store
from app.database import get_db, Community
from app.data_loader import sync_to_pydantic
from app.healthcare_analyzer import analyze_community_healthcare
from app.season_utils import Season, parse_season


router = APIRouter(prefix="/api", tags=["communities"])


@router.get("/communities", response_model=List[CommunityListItem])
async def get_communities():
    """
    Get list of all communities (lightweight view).
    
    Returns basic information for map markers and overview displays.
    """
    return data_store.get_communities_list()


@router.get("/communities/{community_id}", response_model=CommunityRecord)
async def get_community(community_id: str):
    """
    Get complete data for a specific community.
    
    Returns all healthcare, connectivity, and access data with confidence indicators.
    """
    community = data_store.get_community(community_id)
    
    if not community:
        raise HTTPException(
            status_code=404,
            detail=f"Community with ID '{community_id}' not found"
        )
    
    return community


@router.get("/communities/{community_id}/healthcare", response_model=HealthcareData)
async def get_community_healthcare(community_id: str):
    """
    Get healthcare data for a specific community.
    """
    community = data_store.get_community(community_id)
    
    if not community:
        raise HTTPException(
            status_code=404,
            detail=f"Community with ID '{community_id}' not found"
        )
    
    return community.healthcare


@router.get("/communities/{community_id}/connectivity", response_model=ConnectivityData)
async def get_community_connectivity(community_id: str):
    """
    Get connectivity data for a specific community.
    """
    community = data_store.get_community(community_id)
    
    if not community:
        raise HTTPException(
            status_code=404,
            detail=f"Community with ID '{community_id}' not found"
        )
    
    return community.connectivity


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "communities_loaded": data_store.count()
    }


@router.get("/communities/search")
async def search_communities(
    q: str = Query(..., description="Search query"),
    tier: Optional[int] = Query(None, description="Filter by access tier (1-3)"),
    db: Session = Depends(get_db)
):
    """
    Search communities by name or filter by access tier.
    
    Query parameters:
    - q: Search term (searches community names)
    - tier: Optional filter by access tier (1=best, 3=most isolated)
    """
    query = db.query(Community)
    
    if q:
        query = query.filter(Community.name.ilike(f"%{q}%"))
    
    if tier:
        query = query.filter(Community.access_tier == tier)
    
    communities = query.limit(50).all()
    
    return {
        "results": [sync_to_pydantic(c) for c in communities],
        "count": len(communities)
    }


@router.get("/communities/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """
    Get overall statistics about communities and data coverage.
    """
    total = db.query(Community).count()
    
    tier_counts = {}
    for tier in [1, 2, 3]:
        count = db.query(Community).filter(Community.access_tier == tier).count()
        tier_counts[f"tier_{tier}"] = count
    
    avg_completeness = db.query(Community).with_entities(
        Community.data_completeness
    ).all()
    avg = sum(c[0] for c in avg_completeness if c[0]) / len(avg_completeness) if avg_completeness else 0
    
    return {
        "total_communities": total,
        "by_tier": tier_counts,
        "average_data_completeness": round(avg, 3),
        "data_sources": ["OSM", "FCC", "Alaska DOT"]
    }


@router.get("/communities/{community_id}/necessity")
async def get_healthcare_necessity(
    community_id: str,
    season: str = Query("year_round", description="Season: summer, winter, or year_round"),
    db: Session = Depends(get_db)
):
    """
    Calculate healthcare necessity score for a community.
    
    Returns season-adjusted analysis of telehealth need based on:
    - Distance to healthcare facilities
    - Local facility availability
    - Population and access tier
    - Seasonal accessibility
    
    Query parameters:
    - season: summer, winter, or year_round (default)
    """
    season_enum = parse_season(season)
    
    analysis = analyze_community_healthcare(db, community_id, season_enum)
    
    if "error" in analysis:
        raise HTTPException(status_code=404, detail=analysis["error"])
    
    return analysis
