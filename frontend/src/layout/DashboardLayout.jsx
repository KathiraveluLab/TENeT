/**
 * Dashboard Layout Component
 * 
 * Orchestrates the main UI: map view and community info panel.
 * Manages state for community selection and panel visibility.
 */

import React, { useState, useRef, useEffect } from 'react'
import MapViewUpdated from '../components/MapViewUpdated'
import CommunityInfoPanel from '../components/CommunityInfoPanel'
import SeasonSelector from '../components/SeasonSelector'
import SearchBar from '../components/SearchBar'
import StatsPanel from '../components/StatsPanel'
import { fetchCommunity } from '../services/api'
import '../styles/dashboard-layout.css'

const PANEL_ANIMATION_DURATION = 300

const DashboardLayout = () => {
  const [selectedCommunity, setSelectedCommunity] = useState(null)
  const [isPanelOpen, setIsPanelOpen] = useState(false)
  const [isLoadingCommunity, setIsLoadingCommunity] = useState(false)
  const [selectedSeason, setSelectedSeason] = useState('year_round')
  const [searchResults, setSearchResults] = useState(null)
  const closeTimeoutRef = useRef(null)

  const handleCommunitySelect = async (communityId) => {
    setIsLoadingCommunity(true)
    setIsPanelOpen(true)
    
    const { data, error } = await fetchCommunity(communityId)
    
    if (error) {
      console.error('Failed to load community:', error)
      // Could show error state in panel
      setIsLoadingCommunity(false)
      return
    }
    
    setSelectedCommunity(data)
    setIsLoadingCommunity(false)
  }

  const handleClosePanel = () => {
    setIsPanelOpen(false)
    
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current)
    }
    
    closeTimeoutRef.current = setTimeout(() => {
      setSelectedCommunity(null)
    }, PANEL_ANIMATION_DURATION)
  }

  const handleSearch = (results, query) => {
    setSearchResults(results)
    console.log(`Search for "${query}" found ${results.length} communities`)
  }

  const handleClearSearch = () => {
    setSearchResults(null)
  }

  useEffect(() => {
    return () => {
      if (closeTimeoutRef.current) {
        clearTimeout(closeTimeoutRef.current)
      }
    }
  }, [])

  return (
    <div className="dashboard-layout">
      <div className="map-container">
        <SeasonSelector 
          selectedSeason={selectedSeason}
          onSeasonChange={setSelectedSeason}
        />
        <SearchBar 
          onSearch={handleSearch}
          onClear={handleClearSearch}
          onCommunitySelect={handleCommunitySelect}
        />
        <StatsPanel />
        <MapViewUpdated 
          onCommunitySelect={handleCommunitySelect}
          selectedCommunityId={selectedCommunity?.community_id}
          season={selectedSeason}
          searchResults={searchResults}
        />
      </div>
      
      <CommunityInfoPanel
        community={selectedCommunity}
        isOpen={isPanelOpen}
        onClose={handleClosePanel}
        isLoading={isLoadingCommunity}
        season={selectedSeason}
      />
    </div>
  )
}

export default DashboardLayout