import React, { useState } from 'react'
import MapView from '../components/MapView'
import CommunityInfoPanel from '../components/CommunityInfoPanel'
import mockData from '../data/mockCommunityData.json'
import '../styles/dashboard-layout.css'

const DashboardLayout = () => {
  const [selectedCommunity, setSelectedCommunity] = useState(null)
  const [isPanelOpen, setIsPanelOpen] = useState(false)

  const handleCommunitySelect = (communityId) => {
    const community = mockData.communities.find(c => c.id === communityId)
    if (community) {
      setSelectedCommunity(community)
      setIsPanelOpen(true)
    }
  }

  const handleClosePanel = () => {
    setIsPanelOpen(false)
    // Delay clearing the selected community to allow for exit animation
    setTimeout(() => setSelectedCommunity(null), 300)
  }

  return (
    <div className="dashboard-layout">
      <div className="map-container">
        <MapView 
          onCommunitySelect={handleCommunitySelect}
          selectedCommunityId={selectedCommunity?.id}
        />
        
        {/* Demo buttons for testing - remove when map integration is complete */}
        <div className="demo-controls">
          <h4>Demo Community Selection:</h4>
          {mockData.communities.map(community => (
            <button
              key={community.id}
              className="demo-button"
              onClick={() => handleCommunitySelect(community.id)}
            >
              {community.name}
            </button>
          ))}
        </div>
      </div>
      
      <CommunityInfoPanel
        community={selectedCommunity}
        isOpen={isPanelOpen}
        onClose={handleClosePanel}
      />
    </div>
  )
}

export default DashboardLayout