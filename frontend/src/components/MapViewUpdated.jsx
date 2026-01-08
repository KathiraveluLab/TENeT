/**
 * Updated MapView Component
 * 
 * Integrates with TENeT backend API to display communities on an interactive map.
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

// Custom marker icon based on data completeness
const createCommunityIcon = (dataCompleteness, isSelected) => {
  let color = '#6c757d' // Gray for low completeness
  
  if (dataCompleteness >= 0.75) {
    color = '#28a745' // Green for high
  } else if (dataCompleteness >= 0.50) {
    color = '#ffc107' // Yellow for medium
  } else if (dataCompleteness >= 0.25) {
    color = '#fd7e14' // Orange for low-medium
  }
  
  const markerHtml = `
    <div class="community-marker ${isSelected ? 'selected' : ''}" 
         style="background-color: ${color};">
      <div class="marker-dot"></div>
      ${isSelected ? '<div class="marker-pulse"></div>' : ''}
    </div>
  `
  
  return L.divIcon({
    html: markerHtml,
    className: 'community-div-icon',
    iconSize: isSelected ? [24, 24] : [16, 16],
    iconAnchor: isSelected ? [12, 12] : [8, 8]
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

// Main MapView component
const MapViewUpdated = ({ onCommunitySelect, selectedCommunityId }) => {
  const [communities, setCommunities] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [currentZoom, setCurrentZoom] = useState(ALASKA_ZOOM)

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
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        <ZoomTracker onZoomChange={handleZoomChange} />
        
        {communities.map((community) => (
          <Marker
            key={community.community_id}
            position={[community.location.lat, community.location.lon]}
            icon={createCommunityIcon(
              community.data_completeness,
              selectedCommunityId === community.community_id
            )}
            eventHandlers={{
              click: () => handleCommunityClick(community.community_id)
            }}
          >
            <Popup>
              <div className="community-popup">
                <h4>📍 {community.name}</h4>
                {community.region && <p><strong>Region:</strong> {community.region}</p>}
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
      
      <div className="map-legend">
        <h4>Data Completeness</h4>
        <div className="legend-item">
          <span className="legend-marker" style={{backgroundColor: '#28a745'}}></span>
          <span>High (75%+)</span>
        </div>
        <div className="legend-item">
          <span className="legend-marker" style={{backgroundColor: '#ffc107'}}></span>
          <span>Medium (50-75%)</span>
        </div>
        <div className="legend-item">
          <span className="legend-marker" style={{backgroundColor: '#fd7e14'}}></span>
          <span>Low (25-50%)</span>
        </div>
        <div className="legend-item">
          <span className="legend-marker" style={{backgroundColor: '#6c757d'}}></span>
          <span>Limited (&lt;25%)</span>
        </div>
      </div>
    </div>
  )
}

export default MapViewUpdated
