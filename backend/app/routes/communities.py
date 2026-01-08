"""
API routes for community data endpoints.

All endpoints are read-only and return raw data values.
No scoring or feasibility calculations are performed.
"""

from fastapi import APIRouter, HTTPException
from typing import List

from app.models import (
    CommunityRecord, CommunityListItem, HealthcareData, ConnectivityData
)
from app.data_store import data_store


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
