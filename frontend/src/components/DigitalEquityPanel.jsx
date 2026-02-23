/**
 * Digital Equity Panel Component
 * 
 * Displays digital equity analysis and summary statistics.
 * Research-grade visualization with glassmorphism styling.
 */

import React, { useEffect, useState } from 'react'
import { fetchDigitalEquitySummary } from '../services/api'
import '../styles/digital-equity-panel.css'

const DigitalEquityPanel = () => {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const loadSummary = async () => {
      setLoading(true)
      const { data, error } = await fetchDigitalEquitySummary()
      
      if (error) {
        setError(error)
      } else {
        setSummary(data)
      }
      
      setLoading(false)
    }

    loadSummary()
  }, [])

  if (loading) {
    return (
      <div className="equity-panel">
        <div className="equity-loading">Loading equity data...</div>
      </div>
    )
  }

  if (error || !summary) {
    return (
      <div className="equity-panel">
        <div className="equity-error">Unable to load digital equity data</div>
      </div>
    )
  }

  const { classification_summary, affordability_stats, methodology } = summary
  const total = classification_summary.total

  return (
    <div className="equity-panel">
      <h3 className="equity-title">Digital Equity Layer</h3>
      
      <div className="equity-section">
        <h4>Classification Summary</h4>
        <div className="equity-stats">
          <div className="stat-item ready">
            <span className="stat-label">Ready</span>
            <span className="stat-value">{classification_summary.ready}</span>
            <span className="stat-percent">
              {total > 0 ? Math.round((classification_summary.ready / total) * 100) : 0}%
            </span>
          </div>
          
          <div className="stat-item supported">
            <span className="stat-label">Supported</span>
            <span className="stat-value">{classification_summary.supported}</span>
            <span className="stat-percent">
              {total > 0 ? Math.round((classification_summary.supported / total) * 100) : 0}%
            </span>
          </div>
          
          <div className="stat-item excluded">
            <span className="stat-label">Excluded</span>
            <span className="stat-value">{classification_summary.excluded}</span>
            <span className="stat-percent">
              {total > 0 ? Math.round((classification_summary.excluded / total) * 100) : 0}%
            </span>
          </div>
          
          <div className="stat-item insufficient">
            <span className="stat-label">No Data</span>
            <span className="stat-value">{classification_summary.insufficient_data}</span>
            <span className="stat-percent">
              {total > 0 ? Math.round((classification_summary.insufficient_data / total) * 100) : 0}%
            </span>
          </div>
        </div>
      </div>
      
      <div className="equity-section">
        <h4>Affordability Metrics</h4>
        <div className="metric-list">
          <div className="metric-item">
            <span className="metric-label">Affordable:</span>
            <span className="metric-value">{affordability_stats.affordable_count}</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Unaffordable:</span>
            <span className="metric-value">{affordability_stats.unaffordable_count}</span>
          </div>
          {affordability_stats.avg_affordability_ratio && (
            <div className="metric-item">
              <span className="metric-label">Avg. Cost Ratio:</span>
              <span className="metric-value">{affordability_stats.avg_affordability_ratio}%</span>
            </div>
          )}
          {affordability_stats.avg_value_index && (
            <div className="metric-item">
              <span className="metric-label">Avg. Value Index:</span>
              <span className="metric-value">${affordability_stats.avg_value_index}/Mbps</span>
            </div>
          )}
        </div>
      </div>
      
      <div className="equity-section methodology">
        <h4>Methodology</h4>
        <div className="methodology-text">
          <p><strong>Affordability Threshold:</strong> {methodology.affordability_threshold}</p>
          <p><strong>Community Anchor Radius:</strong> {methodology.community_anchor_radius}</p>
        </div>
        <div className="classification-legend">
          <div className="legend-row ready">
            <span className="legend-dot"></span>
            <span>{methodology.classification.ready}</span>
          </div>
          <div className="legend-row supported">
            <span className="legend-dot"></span>
            <span>{methodology.classification.supported}</span>
          </div>
          <div className="legend-row excluded">
            <span className="legend-dot"></span>
            <span>{methodology.classification.excluded}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DigitalEquityPanel
