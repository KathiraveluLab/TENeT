/**
 * Updated MapView Component with Digital Equity Layer
 * 
 * Integrates with TENeT backend API to display communities on an interactive map.
 * Features research-grade visualization with digital equity classification.
 */

import React, { useEffect, useState, useCallback } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import '../styles/map.css'
import { fetchCommunities } from '../services/api'

// Fix for default markers in React Leaflet
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

// Alaska map configuration
const ALASKA_CENTER = [64.2008, -153.0000]
const ALASKA_ZOOM = 5
const MIN_ZOOM = 4
const MAX_ZOOM = 12

const ALASKA_BOUNDS = [
  [51.0, -179.0],
  [71.5, -129.0]
]

// Visualization modes
const VIZ_MODES = {
  ACCESS_TIER: 'access_tier',
  DIGITAL_EQUITY: 'digital_equity',
  VALUE_INDEX: 'value_index'
}

// Research-grade color palette (matte, publication-friendly)
const EQUITY_COLORS = {
  ready: '#6abf69',            // Matte green - Affordable
  supported: '#e6c34d',       // Matte yellow - Community anchor
  excluded: '#c94c4c',        // Matte red - Critical exclusion
  insufficient_data: '#9E9E9E'  // Gray - No data
}

// Access tier colors (legacy)
const TIER_COLORS = {
  1: '#28a745',  // Green - Good access
  2: '#ffc107',  // Yellow - Fair access
  3: '#dc3545'   // Red - Limited access
}

/**
 * Create custom marker icon based on visualization mode.
 * Gemstone design with reduced opacity and white stroke halo.
 */
const createCommunityIcon = (
  community,
  vizMode,
  isSelected
) => {
  let color = '#9E9E9E' // Gray default
  
  if (vizMode === VIZ_MODES.DIGITAL_EQUITY) {
    // Digital equity classification
    const equityClass = community.digital_equity?.equity_classification || 'insufficient_data'
    color = EQUITY_COLORS[equityClass] || EQUITY_COLORS.insufficient_data
  } else if (vizMode === VIZ_MODES.VALUE_INDEX) {
    // Value index heatmap (green = good value, red = poor value)
    const valueIndex = community.digital_equity?.value_index
    if (valueIndex) {
      // Scale: 0-2 = green, 2-10 = yellow to orange, 10+ = red
      if (valueIndex < 2) {
        color = '#90EE90'  // Green
      } else if (valueIndex < 5) {
        color = '#FFD700'  // Yellow
      } else if (valueIndex < 10) {
        color = '#FFA500'  // Orange
      } else {
        color = '#DC143C'  // Red
      }
    }
  } else {
    // Access tier (legacy)
    if (community.access_tier) {
      color = TIER_COLORS[community.access_tier] || color
    } else if (community.data_completeness >= 0.75) {
      color = TIER_COLORS[1]
    } else if (community.data_completeness >= 0.50) {
      color = TIER_COLORS[2]
    } else if (community.data_completeness >= 0.25) {
      color = '#fd7e14'
    }
  }
  
  const size = isSelected ? 20 : 14

  // Confidence heatmap: high confidence → solid, low → faded
  const confidence = community.digital_equity?.confidence || community.data_completeness || 0.5
  const confLevel =
    confidence === 'high' ? 0.9
    : confidence === 'medium' ? 0.7
    : confidence === 'low' ? 0.4
    : (typeof confidence === 'number' ? Math.max(0.3, Math.min(0.95, confidence)) : 0.5)
  const opacity = isSelected ? 0.95 : confLevel
  
  const markerHtml = `
    <div class="gemstone-marker ${isSelected ? 'selected' : ''}" 
         style="
           background-color: ${color};
           width: ${size}px;
           height: ${size}px;
           opacity: ${opacity};
           border: 2px solid white;
           border-radius: 50%;
           box-shadow: 0 0 ${isSelected ? '8px' : '4px'} rgba(0,0,0,0.3);
         ">
    </div>
  `
  
  return L.divIcon({
    html: markerHtml,
    className: 'gemstone-div-icon',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2]
  })
}

// Zoom tracker component
const ZoomTracker = ({ onZoomChange }) => {
  const map = useMap()

  useEffect(() => {
    const handleZoom = () => {
      onZoomChange(map.getZoom())
    }
    
    map.on('zoomend', handleZoom)
    handleZoom()
    
    return () => {
      map.off('zoomend', handleZoom)
    }
  }, [map, onZoomChange])

  return null
}

// URL state sync: writes current layer & region to URL params
const URLStateSync = ({ vizMode }) => {
  const map = useMap()

  useEffect(() => {
    const syncURL = () => {
      const center = map.getCenter()
      const zoom = map.getZoom()
      const params = new URLSearchParams(window.location.search)
      params.set('layer', vizMode)
      params.set('lat', center.lat.toFixed(3))
      params.set('lng', center.lng.toFixed(3))
      params.set('z', zoom)
      const newURL = `${window.location.pathname}?${params.toString()}`
      window.history.replaceState(null, '', newURL)
    }
    map.on('moveend', syncURL)
    syncURL()
    return () => map.off('moveend', syncURL)
  }, [map, vizMode])

  // On mount, restore state from URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const lat = parseFloat(params.get('lat'))
    const lng = parseFloat(params.get('lng'))
    const z = parseInt(params.get('z'), 10)
    if (!isNaN(lat) && !isNaN(lng) && !isNaN(z)) {
      map.setView([lat, lng], z, { animate: false })
    }
  }, [map])

  return null
}

// Main MapView component
const MapViewUpdated = ({ onCommunitySelect, selectedCommunityId, searchResults = null, filteredCommunities = null, vizMode: vizModeProp }) => {
  const [communities, setCommunities] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [currentZoom, setCurrentZoom] = useState(ALASKA_ZOOM)
  
  // Use prop if provided, otherwise fall back to URL / default
  const [vizModeLocal, setVizModeLocal] = useState(() => {
    const params = new URLSearchParams(window.location.search)
    const layer = params.get('layer')
    return Object.values(VIZ_MODES).includes(layer) ? layer : VIZ_MODES.DIGITAL_EQUITY
  })
  const vizMode = vizModeProp || vizModeLocal
  
  // Filter communities based on search results and filters
  const displayedCommunities = filteredCommunities
    ? filteredCommunities
    : (searchResults && Array.isArray(searchResults))
      ? searchResults
      : communities

  // Fetch communities from backend
  useEffect(() => {
    const loadCommunities = async () => {
      setLoading(true)
      const { data, error } = await fetchCommunities()
      
      if (error) {
        setError(error)
        console.error('Failed to load communities:', error)
      } else {
        setCommunities(data)
      }
      
      setLoading(false)
    }

    loadCommunities()
  }, [])

  const handleCommunityClick = useCallback((communityId) => {
    onCommunitySelect(communityId)
  }, [onCommunitySelect])

  const handleZoomChange = useCallback((zoom) => {
    setCurrentZoom(zoom)
  }, [])

  if (loading) {
    return (
      <div className="map-loading">
        <div className="loading-message">Loading Alaska communities...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="map-error">
        <div className="error-message">
          <h3>Unable to load communities</h3>
          <p>{error}</p>
          <p>Make sure the backend server is running on port 8000</p>
        </div>
      </div>
    )
  }

  return (
    <div className="map-container-wrapper">
      <MapContainer
        center={ALASKA_CENTER}
        zoom={ALASKA_ZOOM}
        minZoom={MIN_ZOOM}
        maxZoom={MAX_ZOOM}
        maxBounds={ALASKA_BOUNDS}
        maxBoundsViscosity={1.0}
        className="leaflet-map"
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          subdomains="abcd"
        />
        
        <ZoomTracker onZoomChange={handleZoomChange} />
        <URLStateSync vizMode={vizMode} />
        
        {displayedCommunities.map((community) => (
          <Marker
            key={community.community_id}
            position={[community.location.lat, community.location.lon]}
            icon={createCommunityIcon(
              community,
              vizMode,
              selectedCommunityId === community.community_id
            )}
            eventHandlers={{
              click: () => handleCommunityClick(community.community_id)
            }}
          >
            <Popup className="gemstone-popup">
              <div className="community-popup">
                <h4>📍 {community.name}</h4>
                {community.region && <p><strong>Region:</strong> {community.region}</p>}
                
                {vizMode === VIZ_MODES.DIGITAL_EQUITY && community.digital_equity && (
                  <div className="equity-info">
                    <p><strong>Access Status:</strong> {
                      community.digital_equity.equity_classification === 'ready' ? '✓ Ready' :
                      community.digital_equity.equity_classification === 'supported' ? '◐ Supported' :
                      community.digital_equity.equity_classification === 'excluded' ? '✗ Excluded' :
                      '? Insufficient Data'
                    }</p>
                    {community.digital_equity.affordability_ratio && (
                      <p><strong>Affordability:</strong> {community.digital_equity.affordability_ratio.toFixed(1)}% of income</p>
                    )}
                    {community.digital_equity.has_community_anchor && (
                      <p><strong>Community Anchor:</strong> {community.digital_equity.facility_count_5km} facilities within 5km</p>
                    )}
                  </div>
                )}
                
                {vizMode === VIZ_MODES.VALUE_INDEX && community.digital_equity?.value_index && (
                  <div className="value-info">
                    <p><strong>Value Index:</strong> ${community.digital_equity.value_index.toFixed(2)}/Mbps</p>
                    <p className="value-note">(Lower is better pricing equity)</p>
                  </div>
                )}
                
                <p>
                  <strong>Data Coverage:</strong>{' '}
                  {Math.round(community.data_completeness * 100)}%
                </p>
                <button 
                  onClick={() => handleCommunityClick(community.community_id)}
                  className="explore-community-btn"
                >
                  View Details
                </button>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      
      {/* Dynamic Legend */}
      <div className="map-legend">
        {vizMode === VIZ_MODES.DIGITAL_EQUITY && (
          <>
            <h4>Digital Equity Layer</h4>
            <div className="legend-item">
              <span className="legend-marker gemstone" style={{backgroundColor: EQUITY_COLORS.ready}}></span>
              <span><strong>Ready</strong> - Affordable access</span>
            </div>
            <div className="legend-item">
              <span className="legend-marker gemstone" style={{backgroundColor: EQUITY_COLORS.supported}}></span>
              <span><strong>Supported</strong> - Community anchor</span>
            </div>
            <div className="legend-item">
              <span className="legend-marker gemstone" style={{backgroundColor: EQUITY_COLORS.excluded}}></span>
              <span><strong>Excluded</strong> - Critical gap</span>
            </div>
            <div className="legend-item">
              <span className="legend-marker gemstone" style={{backgroundColor: EQUITY_COLORS.insufficient_data}}></span>
              <span><strong>No Data</strong></span>
            </div>
            <p className="legend-note">Affordability: 2% income threshold | Anchor: 5km radius</p>
          </>
        )}
        
        {vizMode === VIZ_MODES.VALUE_INDEX && (
          <>
            <h4>Value Index ($/Mbps)</h4>
            <div className="legend-item">
              <span className="legend-marker gemstone" style={{backgroundColor: '#90EE90'}}></span>
              <span>&lt; $2/Mbps - Excellent</span>
            </div>
            <div className="legend-item">
              <span className="legend-marker gemstone" style={{backgroundColor: '#FFD700'}}></span>
              <span>$2-5/Mbps - Fair</span>
            </div>
            <div className="legend-item">
              <span className="legend-marker gemstone" style={{backgroundColor: '#FFA500'}}></span>
              <span>$5-10/Mbps - Poor</span>
            </div>
            <div className="legend-item">
              <span className="legend-marker gemstone" style={{backgroundColor: '#DC143C'}}></span>
              <span>&gt; $10/Mbps - Inequitable</span>
            </div>
            <p className="legend-note">Exposes pricing inequity independent of speed</p>
          </>
        )}
        
        {vizMode === VIZ_MODES.ACCESS_TIER && (
          <>
            <h4>Access Tiers</h4>
            <div className="legend-item">
              <span className="legend-marker gemstone" style={{backgroundColor: TIER_COLORS[1]}}></span>
              <span>Tier 1 - Good</span>
            </div>
            <div className="legend-item">
              <span className="legend-marker gemstone" style={{backgroundColor: TIER_COLORS[2]}}></span>
              <span>Tier 2 - Fair</span>
            </div>
            <div className="legend-item">
              <span className="legend-marker gemstone" style={{backgroundColor: TIER_COLORS[3]}}></span>
              <span>Tier 3 - Limited</span>
            </div>
          </>
        )}
        
        {searchResults && (
          <div className="legend-search-info">
            <span>🔍 Showing {searchResults.length} results</span>
          </div>
        )}
      </div>
    </div>
  )
}

export default MapViewUpdated
