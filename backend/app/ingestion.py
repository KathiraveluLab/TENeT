"""
Data ingestion utilities for TENeT.

This module provides sample data ingestion for Alaska communities.
In a production system, this would connect to real data sources like:
- OpenStreetMap Overpass API for healthcare facilities
- FCC broadband data
- Ookla speedtest data
- USGS geographic data

For this prototype, we use curated sample data representing real Alaska communities.
"""

from typing import List
from app.models import (
    CommunityRecord, Location, HealthcareData, ConnectivityData, 
    AccessData, ConfidenceLevel
)


def calculate_data_completeness(community: CommunityRecord) -> float:
    """
    Calculate data completeness score based on confidence levels.
    
    Returns fraction of fields with high/medium confidence (0.0-1.0)
    """
    fields_checked = 0
    fields_confident = 0
    
    # Healthcare fields
    if community.healthcare.facility_count is not None:
        fields_checked += 1
        if community.healthcare.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]:
            fields_confident += 1
    
    # Connectivity fields
    connectivity_fields = [
        community.connectivity.download_mbps,
        community.connectivity.upload_mbps,
        community.connectivity.latency_ms
    ]
    fields_checked += len([f for f in connectivity_fields if f is not None])
    if community.connectivity.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]:
        fields_confident += len([f for f in connectivity_fields if f is not None])
    
    # Access fields
    if community.access.notes or community.access.transportation_types:
        fields_checked += 1
        if community.access.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]:
            fields_confident += 1
    
    if fields_checked == 0:
        return 0.0
    
    return fields_confident / fields_checked


def ingest_sample_communities() -> List[CommunityRecord]:
    """
    Generate sample community data for Alaska villages and towns.
    
    Data is based on publicly available information but simplified for prototype purposes.
    Real implementation would query actual data sources.
    """
    
    communities = [
        CommunityRecord(
            community_id="AK-02185-0001",
            name="Bethel",
            location=Location(lat=60.7922, lon=-161.7558),
            region="Bethel Census Area",
            population=6325,
            healthcare=HealthcareData(
                facility_count=3,
                facility_types=["hospital", "clinic", "dental"],
                source="OSM + Healthsites",
                confidence=ConfidenceLevel.HIGH,
                notes="Yukon-Kuskokwim Delta Regional Hospital serves hub community",
                last_updated="2025-12-15T00:00:00Z"
            ),
            connectivity=ConnectivityData(
                download_mbps=25.0,
                upload_mbps=5.0,
                latency_ms=85.0,
                source="FCC Form 477",
                confidence=ConfidenceLevel.MEDIUM,
                notes="Service available but reliability varies",
                last_updated="2025-06-01T00:00:00Z"
            ),
            access=AccessData(
                notes="Regional hub with year-round air and seasonal barge access",
                seasonal=False,
                confidence=ConfidenceLevel.HIGH,
                transportation_types=["air", "barge"]
            ),
            data_completeness=0.0  # Will be calculated
        ),
        
        CommunityRecord(
            community_id="AK-02070-0001",
            name="Barrow (Utqiaġvik)",
            location=Location(lat=71.2906, lon=-156.7886),
            region="North Slope Borough",
            population=4927,
            healthcare=HealthcareData(
                facility_count=2,
                facility_types=["hospital", "clinic"],
                source="OSM",
                confidence=ConfidenceLevel.HIGH,
                notes="Samuel Simmonds Memorial Hospital",
                last_updated="2025-11-20T00:00:00Z"
            ),
            connectivity=ConnectivityData(
                download_mbps=50.0,
                upload_mbps=10.0,
                latency_ms=None,
                source="FCC",
                confidence=ConfidenceLevel.MEDIUM,
                notes="Fiber optic available in some areas"
            ),
            access=AccessData(
                notes="Air access year-round; ice road in winter",
                seasonal=True,
                confidence=ConfidenceLevel.HIGH,
                transportation_types=["air", "ice_road"]
            ),
            data_completeness=0.0
        ),
        
        CommunityRecord(
            community_id="AK-02290-0001",
            name="Nome",
            location=Location(lat=64.5011, lon=-165.4064),
            region="Nome Census Area",
            population=3699,
            healthcare=HealthcareData(
                facility_count=2,
                facility_types=["hospital", "clinic"],
                source="Healthsites",
                confidence=ConfidenceLevel.HIGH,
                notes="Norton Sound Regional Hospital"
            ),
            connectivity=ConnectivityData(
                download_mbps=30.0,
                upload_mbps=6.0,
                latency_ms=110.0,
                source="FCC + Ookla",
                confidence=ConfidenceLevel.MEDIUM,
                notes="GCI and local ISPs"
            ),
            access=AccessData(
                notes="Hub community with year-round air access, seasonal barge",
                seasonal=True,
                confidence=ConfidenceLevel.HIGH,
                transportation_types=["air", "barge"]
            ),
            data_completeness=0.0
        ),
        
        CommunityRecord(
            community_id="AK-02158-0001",
            name="Juneau",
            location=Location(lat=58.3019, lon=-134.4197),
            region="Juneau City and Borough",
            population=32255,
            healthcare=HealthcareData(
                facility_count=5,
                facility_types=["hospital", "clinic", "urgent_care", "dental"],
                source="OSM",
                confidence=ConfidenceLevel.HIGH,
                notes="State capital with comprehensive healthcare",
                last_updated="2026-01-05T00:00:00Z"
            ),
            connectivity=ConnectivityData(
                download_mbps=100.0,
                upload_mbps=20.0,
                latency_ms=45.0,
                source="Ookla",
                confidence=ConfidenceLevel.HIGH,
                notes="Fiber and cable broadband available"
            ),
            access=AccessData(
                notes="Air and ferry access year-round; no road connection to mainland",
                seasonal=False,
                confidence=ConfidenceLevel.HIGH,
                transportation_types=["air", "ferry"]
            ),
            data_completeness=0.0
        ),
        
        CommunityRecord(
            community_id="AK-02185-0002",
            name="Napakiak",
            location=Location(lat=60.6900, lon=-161.9786),
            region="Bethel Census Area",
            population=378,
            healthcare=HealthcareData(
                facility_count=1,
                facility_types=["health_aide"],
                source="Manual survey",
                confidence=ConfidenceLevel.MEDIUM,
                notes="Village health aide; referrals to Bethel"
            ),
            connectivity=ConnectivityData(
                download_mbps=10.0,
                upload_mbps=2.0,
                latency_ms=None,
                source="FCC",
                confidence=ConfidenceLevel.LOW,
                notes="Limited service; data may be outdated"
            ),
            access=AccessData(
                notes="Air-only access; no road connection",
                seasonal=False,
                confidence=ConfidenceLevel.HIGH,
                transportation_types=["air"]
            ),
            data_completeness=0.0
        ),
        
        CommunityRecord(
            community_id="AK-02220-0001",
            name="Kotzebue",
            location=Location(lat=66.8983, lon=-162.5967),
            region="Northwest Arctic Borough",
            population=3102,
            healthcare=HealthcareData(
                facility_count=2,
                facility_types=["hospital", "clinic"],
                source="OSM",
                confidence=ConfidenceLevel.HIGH,
                notes="Maniilaq Health Center"
            ),
            connectivity=ConnectivityData(
                download_mbps=25.0,
                upload_mbps=5.0,
                latency_ms=120.0,
                source="FCC",
                confidence=ConfidenceLevel.MEDIUM,
                notes="Satellite and microwave connectivity"
            ),
            access=AccessData(
                notes="Hub community; air year-round, barge in summer",
                seasonal=True,
                confidence=ConfidenceLevel.HIGH,
                transportation_types=["air", "barge"]
            ),
            data_completeness=0.0
        ),
        
        CommunityRecord(
            community_id="AK-02110-0001",
            name="Haines",
            location=Location(lat=59.2358, lon=-135.4397),
            region="Haines Borough",
            population=2508,
            healthcare=HealthcareData(
                facility_count=1,
                facility_types=["clinic"],
                source="OSM",
                confidence=ConfidenceLevel.HIGH,
                notes="SEARHC clinic; referrals to Juneau"
            ),
            connectivity=ConnectivityData(
                download_mbps=50.0,
                upload_mbps=10.0,
                latency_ms=55.0,
                source="Ookla",
                confidence=ConfidenceLevel.HIGH,
                notes="Connected via fiber optic"
            ),
            access=AccessData(
                notes="Road and ferry access year-round",
                seasonal=False,
                confidence=ConfidenceLevel.HIGH,
                transportation_types=["road", "ferry"]
            ),
            data_completeness=0.0
        ),
        
        CommunityRecord(
            community_id="AK-02020-0001",
            name="Anchorage",
            location=Location(lat=61.2181, lon=-149.9003),
            region="Anchorage Municipality",
            population=291247,
            healthcare=HealthcareData(
                facility_count=12,
                facility_types=["hospital", "clinic", "urgent_care", "specialty", "dental"],
                source="OSM + verified",
                confidence=ConfidenceLevel.HIGH,
                notes="Major medical hub for Alaska",
                last_updated="2026-01-02T00:00:00Z"
            ),
            connectivity=ConnectivityData(
                download_mbps=250.0,
                upload_mbps=50.0,
                latency_ms=25.0,
                source="Ookla",
                confidence=ConfidenceLevel.HIGH,
                notes="Fiber, cable, and 5G widely available"
            ),
            access=AccessData(
                notes="Major transportation hub with road, rail, air, and sea access",
                seasonal=False,
                confidence=ConfidenceLevel.HIGH,
                transportation_types=["road", "rail", "air", "port"]
            ),
            data_completeness=0.0
        ),
    ]
    
    # Calculate data completeness for each community
    for community in communities:
        community.data_completeness = calculate_data_completeness(community)
    
    return communities


def load_sample_data(data_store) -> int:
    """
    Load sample community data into the data store.
    
    Returns:
        Number of communities loaded
    """
    communities = ingest_sample_communities()
    
    for community in communities:
        data_store.add_community(community)
    
    return len(communities)
