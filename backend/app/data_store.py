"""
In-memory data store for community records.

This module provides a simple data storage layer for prototype/research purposes.
For production, this would be replaced with a proper database.
"""

from typing import Dict, List, Optional
from app.models import CommunityRecord, CommunityListItem


class CommunityDataStore:
    """In-memory storage for community records"""
    
    def __init__(self):
        self._communities: Dict[str, CommunityRecord] = {}
    
    def add_community(self, community: CommunityRecord) -> None:
        """Add or update a community record"""
        self._communities[community.community_id] = community
    
    def get_community(self, community_id: str) -> Optional[CommunityRecord]:
        """Retrieve a specific community by ID"""
        return self._communities.get(community_id)
    
    def get_all_communities(self) -> List[CommunityRecord]:
        """Retrieve all community records"""
        return list(self._communities.values())
    
    def get_communities_list(self) -> List[CommunityListItem]:
        """Retrieve lightweight list of all communities"""
        return [
            CommunityListItem(
                community_id=c.community_id,
                name=c.name,
                location=c.location,
                region=c.region,
                data_completeness=c.data_completeness
            )
            for c in self._communities.values()
        ]
    
    def count(self) -> int:
        """Get total number of communities"""
        return len(self._communities)


# Global data store instance
data_store = CommunityDataStore()
