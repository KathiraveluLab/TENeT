/**
 * Stats Panel Component
 * 
 * Displays community statistics including tier distribution
 */

import React, { useEffect, useState } from 'react'
import '../styles/stats-panel.css'

const StatsPanel = () => {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isExpanded, setIsExpanded] = useState(false)

  useEffect(() => {
    fetch('http://localhost:8000/api/communities/stats')
      .then(res => res.json())
      .then(data => {
        setStats(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch stats:', err)
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="stats-panel">
        <div className="stats-header" onClick={() => setIsExpanded(!isExpanded)}>
          <h3>📊 Statistics</h3>
          <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
        </div>
      </div>
    )
  }

  if (!stats) return null

  return (
    <div className={`stats-panel ${isExpanded ? 'expanded' : ''}`}>
      <div className="stats-header" onClick={() => setIsExpanded(!isExpanded)}>
        <h3>📊 Statistics</h3>
        <span className="stats-count">{stats.total_communities} communities</span>
        <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
      </div>
      
      {isExpanded && (
        <div className="stats-content">
          <div className="stat-section">
            <h4>Access Tiers</h4>
            <div className="tier-stats">
              <div className="tier-item tier-1">
                <span className="tier-label">Tier 1 - Good</span>
                <span className="tier-value">{stats.by_tier.tier_1}</span>
              </div>
              <div className="tier-item tier-2">
                <span className="tier-label">Tier 2 - Fair</span>
                <span className="tier-value">{stats.by_tier.tier_2}</span>
              </div>
              <div className="tier-item tier-3">
                <span className="tier-label">Tier 3 - Limited</span>
                <span className="tier-value">{stats.by_tier.tier_3}</span>
              </div>
            </div>
          </div>

          <div className="stat-section">
            <h4>Data Quality</h4>
            <div className="data-quality">
              <div className="quality-bar">
                <div 
                  className="quality-fill" 
                  style={{ width: `${stats.average_data_completeness * 100}%` }}
                />
              </div>
              <span className="quality-label">
                {(stats.average_data_completeness * 100).toFixed(0)}% Average Completeness
              </span>
            </div>
          </div>

          <div className="stat-section">
            <h4>Data Sources</h4>
            <div className="sources-list">
              {stats.data_sources.map(source => (
                <span key={source} className="source-badge">{source}</span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default StatsPanel
