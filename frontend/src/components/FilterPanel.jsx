/**
 * FilterPanel Component
 *
 * Floating filter controls for the map:
 *  - Show only Tier 4  (mapped to Tier 3 — most isolated)
 *  - Show only Unaffordable
 *  - Show only Critical Exclusion
 *  - Show High Value Index
 *
 * Filters update the displayed community list dynamically.
 */

import React, { useState } from 'react'
import '../styles/filter-panel.css'

const FILTERS = [
  { key: 'tier3',        label: 'Tier 3 (Most Isolated)',  icon: '🏔️' },
  { key: 'unaffordable', label: 'Unaffordable',            icon: '💰' },
  { key: 'excluded',     label: 'Critical Exclusion',      icon: '🚨' },
  { key: 'highValue',    label: 'High Value Index (>$5)',   icon: '📈' },
]

const FilterPanel = ({ communities, onFilteredChange }) => {
  const [activeFilters, setActiveFilters] = useState({})

  const toggleFilter = (key) => {
    const next = { ...activeFilters, [key]: !activeFilters[key] }
    setActiveFilters(next)

    // Apply filters
    const anyActive = Object.values(next).some(Boolean)
    if (!anyActive) {
      onFilteredChange(null) // null = show all
      return
    }

    const filtered = (communities || []).filter((c) => {
      const eq = c.digital_equity || c.digital_equity_data || {}

      if (next.tier3 && c.access_tier !== 3) return false
      if (next.unaffordable && eq.affordability_status !== 'unaffordable') return false
      if (next.excluded && eq.equity_classification !== 'excluded') return false
      if (next.highValue) {
        const vi = eq.value_index
        if (!vi || vi <= 5) return false
      }

      return true
    })

    onFilteredChange(filtered)
  }

  const clearAll = () => {
    setActiveFilters({})
    onFilteredChange(null)
  }

  const activeCount = Object.values(activeFilters).filter(Boolean).length

  return (
    <div className="filter-panel">
      <div className="filter-panel-body">
        {FILTERS.map(({ key, label, icon }) => (
          <label key={key} className={`filter-option ${activeFilters[key] ? 'active' : ''}`}>
            <input
              type="checkbox"
              checked={!!activeFilters[key]}
              onChange={() => toggleFilter(key)}
            />
            <span className="filter-icon">{icon}</span>
            {label}
          </label>
        ))}

        {activeCount > 0 && (
          <button className="filter-clear" onClick={clearAll}>
            Clear all
          </button>
        )}
      </div>
    </div>
  )
}

export default FilterPanel
