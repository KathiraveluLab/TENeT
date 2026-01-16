/**
 * Data Confidence Badge Component
 * 
 * Displays visual indicators for data quality and confidence levels.
 * Part of the transparency-first design philosophy.
 */

import React from 'react'
import '../styles/confidence-badge.css'

const CONFIDENCE_CONFIG = {
  high: {
    label: 'High Confidence',
    icon: '✓',
    className: 'confidence-high',
    description: 'Verified from reliable sources'
  },
  medium: {
    label: 'Medium Confidence',
    icon: '~',
    className: 'confidence-medium',
    description: 'Data available but may be incomplete'
  },
  low: {
    label: 'Low Confidence',
    icon: '?',
    className: 'confidence-low',
    description: 'Limited or outdated data'
  },
  missing: {
    label: 'No Data',
    icon: '✗',
    className: 'confidence-missing',
    description: 'Data not available'
  }
}

function ConfidenceBadge({ level, showLabel = false, showTooltip = true }) {
  const config = CONFIDENCE_CONFIG[level] || CONFIDENCE_CONFIG.missing
  
  return (
    <span 
      className={`confidence-badge ${config.className}`}
      title={showTooltip ? `${config.label}: ${config.description}` : undefined}
      aria-label={`${config.label}: ${config.description}`}
    >
      <span className="confidence-icon">{config.icon}</span>
      {showLabel && <span className="confidence-label">{config.label}</span>}
    </span>
  )
}

export default ConfidenceBadge
