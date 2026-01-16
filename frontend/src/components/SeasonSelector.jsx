/**
 * Season Selector Component
 * 
 * Toggle between Summer, Winter, and Year-Round views.
 * Affects access scoring and telehealth necessity calculations.
 */

import React from 'react'
import '../styles/season-selector.css'

const SEASONS = [
  { value: 'summer', label: 'Summer', icon: '☀️' },
  { value: 'winter', label: 'Winter', icon: '❄️' },
  { value: 'year_round', label: 'Year-Round', icon: '🔄' }
]

const SeasonSelector = ({ selectedSeason, onSeasonChange }) => {
  return (
    <div className="season-selector">
      <div className="season-label">
        <span className="season-icon">📅</span>
        <span>Season:</span>
      </div>
      <div className="season-buttons">
        {SEASONS.map(season => (
          <button
            key={season.value}
            className={`season-button ${selectedSeason === season.value ? 'active' : ''}`}
            onClick={() => onSeasonChange(season.value)}
            title={`View ${season.label} accessibility`}
          >
            <span className="season-button-icon">{season.icon}</span>
            <span className="season-button-label">{season.label}</span>
          </button>
        ))}
      </div>
      <div className="season-info">
        {selectedSeason === 'summer' && (
          <p>🌊 Summer: Water routes open, ice roads closed</p>
        )}
        {selectedSeason === 'winter' && (
          <p>🧊 Winter: Ice roads accessible, rivers frozen</p>
        )}
        {selectedSeason === 'year_round' && (
          <p>📊 Year-Round: Conservative baseline (worst-case)</p>
        )}
      </div>
    </div>
  )
}

export default SeasonSelector
