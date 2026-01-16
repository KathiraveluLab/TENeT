/**
 * Data Completeness Indicator Component
 * 
 * Shows overall data quality for a community as a visual progress bar.
 */

import React from 'react'
import '../styles/completeness-indicator.css'

function CompletenessIndicator({ score, showPercentage = true }) {
  const percentage = Math.round(score * 100)
  
  // Determine quality level
  let qualityClass = 'low'
  let qualityLabel = 'Limited Data'
  
  if (percentage >= 75) {
    qualityClass = 'high'
    qualityLabel = 'Good Coverage'
  } else if (percentage >= 50) {
    qualityClass = 'medium'
    qualityLabel = 'Moderate Coverage'
  }
  
  return (
    <div className="completeness-indicator">
      <div className="completeness-header">
        <span className="completeness-label">Data Coverage</span>
        {showPercentage && (
          <span className={`completeness-percentage ${qualityClass}`}>
            {percentage}%
          </span>
        )}
      </div>
      <div className="completeness-bar-container">
        <div 
          className={`completeness-bar ${qualityClass}`}
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={percentage}
          aria-valuemin="0"
          aria-valuemax="100"
          aria-label={`${qualityLabel}: ${percentage}% data coverage`}
        />
      </div>
      <span className="completeness-quality-label">{qualityLabel}</span>
    </div>
  )
}

export default CompletenessIndicator
