/**
 * Dashboard Layout — TopNav + ControlDrawer + Map canvas.
 */

import React, { useState, useRef, useEffect } from 'react'
import TopNav from '../components/layout/TopNav'
import ControlDrawer from '../components/layout/ControlDrawer'
import MapViewUpdated from '../components/MapViewUpdated'
import CommunityInfoPanel from '../components/CommunityInfoPanel'
import { fetchCommunity, fetchCommunities } from '../services/api'
import '../styles/dashboard-layout.css'

const PANEL_ANIMATION_DURATION = 300

const VIZ_MODES = {
  ACCESS_TIER: 'access_tier',
  DIGITAL_EQUITY: 'digital_equity',
  VALUE_INDEX: 'value_index'
}

const DashboardLayout = () => {
  const [selectedCommunity, setSelectedCommunity] = useState(null)
  const [isPanelOpen, setIsPanelOpen] = useState(false)
  const [isLoadingCommunity, setIsLoadingCommunity] = useState(false)
  const [selectedSeason, setSelectedSeason] = useState(() => {
    try { return localStorage.getItem('tenet_season') || 'year_round' } catch { return 'year_round' }
  })
  const [searchResults, setSearchResults] = useState(null)
  const [allCommunities, setAllCommunities] = useState([])
  const [filteredCommunities, setFilteredCommunities] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const [vizMode, setVizMode] = useState(() => {
    const params = new URLSearchParams(window.location.search)
    const layer = params.get('layer')
    const saved = localStorage.getItem('tenet_layer')
    return Object.values(VIZ_MODES).includes(layer)
      ? layer
      : Object.values(VIZ_MODES).includes(saved)
        ? saved
        : VIZ_MODES.DIGITAL_EQUITY
  })

  const closeTimeoutRef = useRef(null)

  // Persist preferences
  useEffect(() => { try { localStorage.setItem('tenet_layer', vizMode) } catch {} }, [vizMode])
  useEffect(() => { try { localStorage.setItem('tenet_season', selectedSeason) } catch {} }, [selectedSeason])

  useEffect(() => {
    const load = async () => {
      const { data } = await fetchCommunities()
      if (data) setAllCommunities(data)
    }
    load()
  }, [])

  const handleCommunitySelect = async (communityId) => {
    setIsLoadingCommunity(true)
    setIsPanelOpen(true)
    const { data, error } = await fetchCommunity(communityId)
    if (error) { console.error('Failed to load community:', error); setIsLoadingCommunity(false); return }
    setSelectedCommunity(data)
    setIsLoadingCommunity(false)
  }

  const handleClosePanel = () => {
    setIsPanelOpen(false)
    if (closeTimeoutRef.current) clearTimeout(closeTimeoutRef.current)
    closeTimeoutRef.current = setTimeout(() => setSelectedCommunity(null), PANEL_ANIMATION_DURATION)
  }

  const handleSearch = (results, _query) => setSearchResults(results)
  const handleClearSearch = () => setSearchResults(null)

  useEffect(() => () => { if (closeTimeoutRef.current) clearTimeout(closeTimeoutRef.current) }, [])

  return (
    <div className="dashboard-layout">
      {/* ─── Sticky Top Nav ─── */}
      <TopNav
        vizMode={vizMode}
        onVizModeChange={setVizMode}
        season={selectedSeason}
        onSeasonChange={setSelectedSeason}
        onSearch={handleSearch}
        onClearSearch={handleClearSearch}
        onCommunitySelect={handleCommunitySelect}
      />

      {/* ─── Content: Drawer + Map ─── */}
      <div className="dashboard-content">
        <ControlDrawer
          isOpen={drawerOpen}
          onToggle={() => setDrawerOpen(v => !v)}
          communities={allCommunities}
          onFilteredChange={setFilteredCommunities}
        />

        <div className={`map-canvas ${drawerOpen ? 'map-canvas--shifted' : ''}`}>
          <MapViewUpdated
            onCommunitySelect={handleCommunitySelect}
            selectedCommunityId={selectedCommunity?.community_id}
            season={selectedSeason}
            searchResults={searchResults}
            filteredCommunities={filteredCommunities}
            vizMode={vizMode}
          />
        </div>
      </div>

      {/* ─── Community Detail Panel (slides from right) ─── */}
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