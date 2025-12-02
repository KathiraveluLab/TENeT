import React, { useState } from 'react'
import InfoRow from './InfoRow'
import '../styles/community-info-panel.css'

const CommunityInfoPanel = ({ community, isOpen, onClose }) => {
  const [isDetailsExpanded, setIsDetailsExpanded] = useState(false)

  if (!community) return null

const formatCoordinates = (coordinates) => {
  if (!coordinates || coordinates.lat == null || coordinates.lon == null) return 'N/A'
  return `${coordinates.lat.toFixed(4)}°, ${coordinates.lon.toFixed(4)}°`
}

const formatAccessTypes = (types) => {
  if (!types || types.length === 0) return 'No data available'
  return types.map(type => 
    type.charAt(0).toUpperCase() + type.slice(1)
  ).join(', ')
}


  return (
    <div className={`community-info-panel ${isOpen ? 'open' : ''}`}>
      <div className="panel-header">
        <h2 className="panel-title">{community.name}</h2>
        <button 
          className="close-button"
          onClick={onClose}
          aria-label="Close community information panel"
        >
          ×
        </button>
      </div>

      <div className="panel-content">
        {/* Basic Community Details */}
        <section className="info-section">
          <h3 className="section-title">🏘️ Community Details</h3>
          <div className="section-content">
            <InfoRow label="Region" value={community.region} className="full-width" />
            <InfoRow label="Population" value={community.population} />
            <InfoRow label="Coordinates" value={formatCoordinates(community.coordinates)} />
          </div>
        </section>

        {/* Healthcare Overview */}
        <section className="info-section">
          <h3 className="section-title">🏥 Healthcare Overview</h3>
          <div className="section-content">
            <InfoRow 
              label="Health Facilities" 
              value={community.clinic_count > 0 ? `${community.clinic_count} clinic${community.clinic_count > 1 ? 's' : ''}` : 'None'} 
            />
            <InfoRow 
              label="Specialist Availability" 
              value={community.specialist_availability}
            />
            <InfoRow 
              label="Nearest Health Hub" 
              value={community.nearest_hub ? `${community.nearest_hub.name} (${community.nearest_hub.distance_km} km)` : null}
              className="full-width"
            />
          </div>
        </section>

        {/* Connectivity Overview */}
        <section className="info-section">
          <h3 className="section-title">📡 Connectivity Overview</h3>
          <div className="section-content">
            <InfoRow 
              label="Download Speed" 
              value={community.connectivity?.download_mbps ? `${community.connectivity.download_mbps} Mbps` : null}
            />
            <InfoRow 
              label="Upload Speed" 
              value={community.connectivity?.upload_mbps ? `${community.connectivity.upload_mbps} Mbps` : null}
            />
            <InfoRow 
              label="Latency" 
              value={community.connectivity?.latency_ms ? `${community.connectivity.latency_ms} ms` : null}
              className="full-width"
            />
          </div>
        </section>

        {/* Transportation / Access */}
        <section className="info-section">
          <h3 className="section-title">🚁 Access & Transportation</h3>
          <div className="section-content">
            <InfoRow 
              label="Access Types" 
              value={formatAccessTypes(community.access?.types)}
              className="full-width"
            />
            {community.access?.seasonality_note && (
              <InfoRow 
                label="Seasonal Notes" 
                value={community.access.seasonality_note}
                className="seasonal-note full-width"
              />
            )}
          </div>
        </section>

        {/* Collapsible More Details */}
        <section className="info-section collapsible">
          <button 
            className="section-toggle"
            onClick={() => setIsDetailsExpanded(!isDetailsExpanded)}
            aria-expanded={isDetailsExpanded}
          >
            <h3 className="section-title">📊 More Details</h3>
            <span className={`toggle-icon ${isDetailsExpanded ? 'expanded' : ''}`}>
              ▼
            </span>
          </button>
          
          {isDetailsExpanded && (
            <div className="section-content expanded-content">
              <InfoRow label="Community ID" value={community.id} />
              <InfoRow label="Data Source" value={community.metadata?.source} />
              <InfoRow label="Last Updated" value={community.metadata?.last_updated} />
              
              {/* Raw connectivity data for debugging */}
              {community.connectivity && (
                <div className="raw-data">
                  <h4 className="subsection-title">Raw Connectivity Data</h4>
                  <pre className="json-display">
                    {useMemo(() => JSON.stringify(community.connectivity, null, 2), [community.connectivity])}
                  </pre>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

export default CommunityInfoPanel