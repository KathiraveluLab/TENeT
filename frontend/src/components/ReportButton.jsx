/**
 * ReportButton Component
 *
 * Provides download buttons for PDF / HTML reports.
 * Works for both individual communities and state summary.
 */

import React, { useState } from 'react'
import '../styles/report-button.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

const ReportButton = ({ communityId, communityName }) => {
  const [downloading, setDownloading] = useState(false)

  const downloadReport = async (fmt = 'html') => {
    setDownloading(true)

    try {
      const url = communityId
        ? `${API_BASE}/communities/${communityId}/report?fmt=${fmt}`
        : `${API_BASE}/state-summary/report?fmt=${fmt}`

      const resp = await fetch(url)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

      const blob = await resp.blob()
      const anchor = document.createElement('a')
      anchor.href = URL.createObjectURL(blob)

      const filename = communityId
        ? `${(communityName || communityId).replace(/\s+/g, '_')}_report.${fmt}`
        : `TENeT_State_Summary.${fmt}`

      anchor.download = filename
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(anchor.href)
    } catch (err) {
      console.error('Report download failed:', err)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="report-button-group">
      <button
        className="report-btn"
        onClick={() => downloadReport('html')}
        disabled={downloading}
        title="Download HTML report"
      >
        {downloading ? '⏳' : '📄'} {communityId ? 'Report' : 'State Summary'}
      </button>
    </div>
  )
}

export default ReportButton
