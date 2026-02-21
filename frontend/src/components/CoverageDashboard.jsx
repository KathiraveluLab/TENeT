/**
 * CoverageDashboard Component
 *
 * Displays data coverage / transparency metrics from /api/system/coverage.
 * Shows % of communities with income, broadband, and clinic proximity data.
 */

import React, { useEffect, useState } from 'react'
import { fetchSystemCoverage } from '../services/api'
import '../styles/coverage-dashboard.css'

const Bar = ({ pct, label, color }) => (
  <div className="coverage-bar-row">
    <span className="coverage-bar-label">{label}</span>
    <div className="coverage-bar-track">
      <div
        className="coverage-bar-fill"
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
    <span className="coverage-bar-value">{pct}%</span>
  </div>
)

const CoverageDashboard = ({ onClose }) => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      const { data: d, error } = await fetchSystemCoverage()
      if (!error) setData(d)
      setLoading(false)
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="coverage-dashboard">
        <div className="coverage-header">
          <h3>Data Coverage</h3>
          {onClose && <button className="coverage-close" onClick={onClose}>×</button>}
        </div>
        <p className="coverage-loading">Loading coverage data…</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="coverage-dashboard">
        <div className="coverage-header">
          <h3>Data Coverage</h3>
          {onClose && <button className="coverage-close" onClick={onClose}>×</button>}
        </div>
        <p className="coverage-error">Unable to load coverage data.</p>
      </div>
    )
  }

  return (
    <div className="coverage-dashboard">
      <div className="coverage-header">
        <h3>Data Coverage</h3>
        {onClose && <button className="coverage-close" onClick={onClose}>×</button>}
      </div>

      <div className="coverage-stats">
        <div className="coverage-stat">
          <span className="stat-number">{data.total_communities}</span>
          <span className="stat-label">Communities</span>
        </div>
        <div className="coverage-stat">
          <span className="stat-number">{data.total_facilities}</span>
          <span className="stat-label">Facilities</span>
        </div>
      </div>

      <div className="coverage-bars">
        <Bar pct={data.pct_with_income_data} label="Income Data" color="#28a745" />
        <Bar pct={data.pct_with_broadband_data} label="Broadband Data" color="#007bff" />
        <Bar pct={data.pct_with_clinic_proximity} label="Clinic Proximity" color="#fd7e14" />
      </div>

      <div className="coverage-meta">
        <p>Dataset v{data.dataset_version}</p>
        {data.data_timestamps?.communities_last_updated && (
          <p>Communities updated: {new Date(data.data_timestamps.communities_last_updated).toLocaleDateString()}</p>
        )}
      </div>
    </div>
  )
}

export default CoverageDashboard
