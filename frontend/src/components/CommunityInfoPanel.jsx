/**
 * Community Information Panel Component
 * 
 * Displays comprehensive community data including:
 * - Healthcare facilities
 * - Connectivity metrics
 * - Access/transportation information
 * - Data confidence indicators
 * 
 * Design principles:
 * - Raw values only (no derived scores)
 * - Explicit confidence tracking
 * - Transparent handling of missing data
 */

import React, { useState } from 'react'
import InfoRow from './InfoRow'
import ConfidenceBadge from './ConfidenceBadge'
import CompletenessIndicator from './CompletenessIndicator'
import { fetchNecessityScore } from '../services/api'
import '../styles/community-info-panel.css'

const CommunityInfoPanel = ({ community, isOpen, onClose, isLoading = false, season = 'year_round' }) => {
  const [isDetailsExpanded, setIsDetailsExpanded] = useState(false)
  const [necessityData, setNecessityData] = useState(null)
  const [loadingNecessity, setLoadingNecessity] = useState(false)

  // Fetch necessity score when community or season changes
  React.useEffect(() => {
    if (community?.community_id && season) {
      setLoadingNecessity(true)
      fetchNecessityScore(community.community_id, season)
        .then(({ data, error }) => {
          if (error) {
            console.error('Failed to fetch necessity score:', error)
          } else {
            setNecessityData(data)
          }
          setLoadingNecessity(false)
        })
    }
  }, [community?.community_id, season])

  if (!community && !isLoading) return null

  const formatCoordinates = (location) => {
    if (!location || location.lat == null || location.lon == null) return 'N/A'
    return `${location.lat.toFixed(4)}°, ${location.lon.toFixed(4)}°`
  }

  const formatList = (items) => {
    if (!items || items.length === 0) return 'None'
    return items.map(item => item.replace(/_/g, ' ').charAt(0).toUpperCase() + item.slice(1).replace(/_/g, ' ')).join(', ')
  }

  const formatDate = (isoDate) => {
    if (!isoDate) return 'Unknown'
    try {
      return new Date(isoDate).toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      })
    } catch {
      return 'Invalid date'
    }
  }

  const getAccessTierLabel = (tier) => {
    const labels = { 1: 'Good', 2: 'Fair', 3: 'Limited' }
    return labels[tier] || 'Unknown'
  }

  const getAccessTierColor = (tier) => {
    const colors = { 1: '#28a745', 2: '#ffc107', 3: '#dc3545' }
    return colors[tier] || '#6c757d'
  }

  return (
    <div className={`community-info-panel ${isOpen ? 'open' : ''}`}>
      <div className="panel-header">
        <h2 className="panel-title">
          {isLoading ? 'Loading...' : community?.name || 'No Community Selected'}
        </h2>
        <button 
          className="close-button"
          onClick={onClose}
          aria-label="Close community information panel"
        >
          ×
        </button>
      </div>

      {isLoading ? (
        <div className="panel-content loading">
          <div className="loading-spinner">Loading community data...</div>
        </div>
      ) : community ? (
        <div className="panel-content">
          {/* Data Completeness Overview */}
          <section className="info-section">
            <CompletenessIndicator score={community.data_completeness} />
          </section>

          {/* Necessity Score & Access Tier */}
          {necessityData && (
            <section className="info-section necessity-section">
              <h3 className="section-title">🎯 Telehealth Priority</h3>
              <div className="section-content">
                <div className="necessity-score-card" style={{ borderLeftColor: necessityData.priority_color }}>
                  <div className="necessity-score-value">{necessityData.necessity_score.toFixed(1)}</div>
                  <div className="necessity-score-label">Necessity Score</div>
                  <div className="necessity-priority" style={{ color: necessityData.priority_color }}>
                    {necessityData.priority_level}
                  </div>
                </div>
                <InfoRow 
                  label="Access Tier" 
                  value={
                    <span style={{ color: getAccessTierColor(necessityData.access_tier), fontWeight: 'bold' }}>
                      Tier {necessityData.access_tier} - {getAccessTierLabel(necessityData.access_tier)}
                    </span>
                  }
                  className="full-width"
                />
                <InfoRow 
                  label="Season" 
                  value={season.replace('_', ' ').toUpperCase()}
                />
                <InfoRow 
                  label="Recommendation" 
                  value={necessityData.recommendation}
                  className="full-width notes"
                />
              </div>
            </section>
          )}

          {/* Basic Community Details */}
          <section className="info-section">
            <h3 className="section-title">🏘️ Community Details</h3>
            <div className="section-content">
              <InfoRow label="Region" value={community.region || 'N/A'} className="full-width" />
              <InfoRow label="Population" value={community.population || 'N/A'} />
              <InfoRow label="Coordinates" value={formatCoordinates(community.location)} />
              <InfoRow label="Community ID" value={community.community_id} className="full-width community-id" />
            </div>
          </section>

          {/* Healthcare Overview */}
          <section className="info-section">
            <div className="section-header">
              <h3 className="section-title">🏥 Healthcare</h3>
              <ConfidenceBadge level={community.healthcare.confidence} />
            </div>
            <div className="section-content">
              <InfoRow 
                label="Facilities" 
                value={community.healthcare.facility_count !== null ? community.healthcare.facility_count : 'No data'}
              />
              <InfoRow 
                label="Types" 
                value={formatList(community.healthcare.facility_types)}
                className="full-width"
              />
              <InfoRow 
                label="Source" 
                value={community.healthcare.source}
                className="data-source"
              />
              {community.healthcare.notes && (
                <InfoRow 
                  label="Notes" 
                  value={community.healthcare.notes}
                  className="full-width notes"
                />
              )}
              {community.healthcare.last_updated && (
                <InfoRow 
                  label="Updated" 
                  value={formatDate(community.healthcare.last_updated)}
                  className="last-updated"
                />
              )}
            </div>
          </section>

          {/* Connectivity Overview */}
          <section className="info-section">
            <div className="section-header">
              <h3 className="section-title">📡 Connectivity</h3>
              <ConfidenceBadge level={community.connectivity.confidence} />
            </div>
            <div className="section-content">
              <InfoRow 
                label="Download" 
                value={community.connectivity.download_mbps !== null ? `${community.connectivity.download_mbps} Mbps` : 'No data'}
              />
              <InfoRow 
                label="Upload" 
                value={community.connectivity.upload_mbps !== null ? `${community.connectivity.upload_mbps} Mbps` : 'No data'}
              />
              <InfoRow 
                label="Latency" 
                value={community.connectivity.latency_ms !== null ? `${community.connectivity.latency_ms} ms` : 'No data'}
                className="full-width"
              />
              <InfoRow 
                label="Source" 
                value={community.connectivity.source}
                className="data-source"
              />
              {community.connectivity.notes && (
                <InfoRow 
                  label="Notes" 
                  value={community.connectivity.notes}
                  className="full-width notes"
                />
              )}
              {community.connectivity.last_updated && (
                <InfoRow 
                  label="Updated" 
                  value={formatDate(community.connectivity.last_updated)}
                  className="last-updated"
                />
              )}
            </div>
          </section>

          {/* Transportation / Access */}
          <section className="info-section">
            <div className="section-header">
              <h3 className="section-title">🚁 Access & Transportation</h3>
              <ConfidenceBadge level={community.access.confidence} />
            </div>
            <div className="section-content">
              <InfoRow 
                label="Methods" 
                value={formatList(community.access.transportation_types)}
                className="full-width"
              />
              {community.access.seasonal !== null && (
                <InfoRow 
                  label="Seasonal" 
                  value={community.access.seasonal ? 'Yes' : 'No'}
                />
              )}
              {community.access.notes && (
                <InfoRow 
                  label="Notes" 
                  value={community.access.notes}
                  className="full-width notes"
                />
              )}
            </div>
          </section>

          {/* Collapsible Raw Data */}
          <section className="info-section collapsible">
            <button 
              className="section-toggle"
              onClick={() => setIsDetailsExpanded(!isDetailsExpanded)}
              aria-expanded={isDetailsExpanded}
            >
              <h3 className="section-title">📊 Raw Data</h3>
              <span className={`toggle-icon ${isDetailsExpanded ? 'expanded' : ''}`}>
                ▼
              </span>
            </button>
            
            {isDetailsExpanded && (
              <div className="section-content expanded-content">
                <div className="raw-data">
                  <pre className="json-display">
                    {JSON.stringify(community, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </section>
        </div>
      ) : null}
    </div>
  )
}

export default CommunityInfoPanel