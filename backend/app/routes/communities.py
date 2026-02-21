"""
API routes for community data endpoints.

All endpoints are read-only and return raw data values.
Enhanced with season-aware analysis and healthcare necessity scoring.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import (
    CommunityRecord, CommunityListItem, HealthcareData, ConnectivityData, Location, DigitalEquityData
)
from app.database import get_db, Community
from app.data_loader import sync_to_pydantic
from app.healthcare_analyzer import analyze_community_healthcare
from app.season_utils import Season, parse_season
from app.digital_equity_integration import (
    compute_digital_equity_for_community,
    convert_to_pydantic as equity_to_pydantic,
    update_community_equity_data,
    batch_update_equity_data
)


router = APIRouter(prefix="/api", tags=["communities"])


@router.get("/communities", response_model=List[CommunityListItem])
async def get_communities(db: Session = Depends(get_db)):
    """
    Get list of all communities (lightweight view).
    
    Returns basic information for map markers and overview displays.
    """
    communities = db.query(Community).all()
    return [CommunityListItem(
        community_id=c.community_id,
        name=c.name,
        location=Location(lat=c.latitude, lon=c.longitude),
        region=c.region,
        population=c.population,
        data_completeness=c.data_completeness
    ) for c in communities]


@router.get("/communities/search")
async def search_communities(
    q: Optional[str] = Query(None, description="Search query"),
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


@router.get("/communities/{community_id}", response_model=CommunityRecord)
async def get_community(community_id: str, db: Session = Depends(get_db)):
    """
    Get complete data for a specific community.
    
    Returns all healthcare, connectivity, and access data with confidence indicators.
    """
    community = db.query(Community).filter(Community.community_id == community_id).first()
    
    if not community:
        raise HTTPException(
            status_code=404,
            detail=f"Community with ID '{community_id}' not found"
        )
    
    return sync_to_pydantic(community)


@router.get("/communities/{community_id}/healthcare", response_model=HealthcareData)
async def get_community_healthcare(community_id: str, db: Session = Depends(get_db)):
    """
    Get healthcare data for a specific community.
    """
    community = db.query(Community).filter(Community.community_id == community_id).first()
    
    if not community:
        raise HTTPException(
            status_code=404,
            detail=f"Community with ID '{community_id}' not found"
        )
    
    return sync_to_pydantic(community).healthcare


@router.get("/communities/{community_id}/connectivity", response_model=ConnectivityData)
async def get_community_connectivity(community_id: str, db: Session = Depends(get_db)):
    """
    Get connectivity data for a specific community.
    """
    community = db.query(Community).filter(Community.community_id == community_id).first()
    
    if not community:
        raise HTTPException(
            status_code=404,
            detail=f"Community with ID '{community_id}' not found"
        )
    
    return sync_to_pydantic(community).connectivity


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    """
    total = db.query(Community).count()
    return {
        "status": "healthy",
        "communities_loaded": total
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


@router.get("/communities/{community_id}/digital-equity", response_model=DigitalEquityData)
async def get_digital_equity(
    community_id: str,
    refresh: bool = Query(False, description="Force refresh of equity analysis"),
    db: Session = Depends(get_db)
):
    """
    Get digital equity analysis for a specific community.
    
    Returns comprehensive analysis of real-world telehealth access including:
    - Affordability status (based on 2% income threshold)
    - Continuity of care (community healthcare anchors within 5km)
    - Value index (cost per Mbps - pricing equity)
    - Overall equity classification (ready/supported/excluded)
    
    Query parameters:
    - refresh: Force recalculation of equity metrics (default: false)
    """
    community = db.query(Community).filter(Community.community_id == community_id).first()
    
    if not community:
        raise HTTPException(
            status_code=404,
            detail=f"Community with ID '{community_id}' not found"
        )
    
    # Check if we need to compute or refresh
    if refresh or not community.digital_equity_data:
        metrics = compute_digital_equity_for_community(community, db)
        if not metrics:
            raise HTTPException(
                status_code=500,
                detail="Unable to compute digital equity metrics - insufficient data"
            )
        equity_data = equity_to_pydantic(metrics)
        community.digital_equity_data = equity_data.dict()
        db.commit()
        return equity_data
    
    # Return existing data
    return sync_to_pydantic(community).digital_equity


@router.get("/digital-equity/summary")
async def get_digital_equity_summary(db: Session = Depends(get_db)):
    """
    Get summary statistics for digital equity across all communities.
    
    Returns aggregate counts by equity classification:
    - ready: Affordable home internet
    - supported: Unaffordable but community anchor available
    - excluded: Critical exclusion (no affordable access, no facility)
    - insufficient_data: Cannot determine
    """
    communities = db.query(Community).all()
    
    summary = {
        "ready": 0,
        "supported": 0,
        "excluded": 0,
        "insufficient_data": 0,
        "total": len(communities)
    }
    
    affordability_stats = {
        "affordable_count": 0,
        "unaffordable_count": 0,
        "avg_affordability_ratio": None,
        "avg_value_index": None
    }
    
    ratios = []
    value_indices = []
    
    for community in communities:
        if community.digital_equity_data:
            equity_data = community.digital_equity_data
            classification = equity_data.get("equity_classification", "insufficient_data")
            summary[classification] = summary.get(classification, 0) + 1
            
            if equity_data.get("affordability_ratio"):
                ratios.append(equity_data["affordability_ratio"])
            
            if equity_data.get("value_index"):
                value_indices.append(equity_data["value_index"])
            
            if equity_data.get("affordability_status") == "affordable":
                affordability_stats["affordable_count"] += 1
            elif equity_data.get("affordability_status") == "unaffordable":
                affordability_stats["unaffordable_count"] += 1
    
    if ratios:
        affordability_stats["avg_affordability_ratio"] = round(sum(ratios) / len(ratios), 2)
    
    if value_indices:
        affordability_stats["avg_value_index"] = round(sum(value_indices) / len(value_indices), 2)
    
    return {
        "classification_summary": summary,
        "affordability_stats": affordability_stats,
        "methodology": {
            "affordability_threshold": "2% of monthly income (UN Broadband Commission standard)",
            "community_anchor_radius": "5 km",
            "classification": {
                "ready": "Affordable home internet (green)",
                "supported": "Unaffordable but healthcare facility nearby (yellow)",
                "excluded": "Unaffordable with no nearby facility (red)",
                "insufficient_data": "Cannot determine (gray)"
            }
        }
    }


@router.post("/digital-equity/batch-update")
async def batch_update_digital_equity(
    limit: Optional[int] = Query(None, description="Limit number of communities to update"),
    db: Session = Depends(get_db)
):
    """
    Batch update digital equity data for all communities.
    
    This endpoint computes and stores equity metrics for multiple communities.
    Use this to populate the digital equity layer after initial data load.
    
    Query parameters:
    - limit: Optional limit on number of communities to process
    
    Returns count of successfully updated communities.
    """
    updated_count = batch_update_equity_data(db, limit)
    
    return {
        "status": "success",
        "updated_count": updated_count,
        "message": f"Digital equity data updated for {updated_count} communities"
    }

