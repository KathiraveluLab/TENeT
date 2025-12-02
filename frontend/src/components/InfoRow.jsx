import React from 'react'

const InfoRow = ({ label, value, className = '' }) => {
  if (!value && value !== 0) {
    return (
      <div className={`info-row ${className}`}>
        <span className="info-label">{label}:</span>
        <span className="info-value no-data">No data available</span>
      </div>
    )
  }

  return (
    <div className={`info-row ${className}`}>
      <span className="info-label">{label}:</span>
      <span className="info-value">{value}</span>
    </div>
  )
}

export default InfoRow