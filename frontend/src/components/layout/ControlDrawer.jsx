/**
 * ControlDrawer — Collapsible left-side drawer.
 *
 * Contains: Filters, Statistics, Data Coverage, State Summary.
 * Slides in/out with glass-effect styling.
 */
import React, { useState } from 'react'
import FilterPanel from '../FilterPanel'
import StatsPanel from '../StatsPanel'
import CoverageDashboard from '../CoverageDashboard'

const ControlDrawer = ({ isOpen, onToggle, communities, onFilteredChange }) => {
  const [activeSection, setActiveSection] = useState(null)

  const toggle = (section) => {
    setActiveSection(prev => (prev === section ? null : section))
  }

  return (
    <>
      {/* Toggle button always visible */}
      <button
        className={`drawer-toggle ${isOpen ? 'drawer-toggle--open' : ''}`}
        onClick={onToggle}
        title={isOpen ? 'Close panel' : 'Open panel'}
        aria-label={isOpen ? 'Close control panel' : 'Open control panel'}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="1" y="2" width="5" height="12" rx="1" stroke="currentColor" strokeWidth="1.5" fill={isOpen ? 'currentColor' : 'none'} opacity={isOpen ? 0.3 : 1}/>
          <rect x="8" y="2" width="7" height="12" rx="1" stroke="currentColor" strokeWidth="1.5"/>
        </svg>
      </button>

      {/* Drawer panel */}
      <aside className={`drawer ${isOpen ? 'drawer--open' : ''}`}>
        <div className="drawer__inner">
          <div className="drawer__header">
            <h2 className="drawer__title">Controls</h2>
            <button className="drawer__close" onClick={onToggle} aria-label="Close">×</button>
          </div>

          {/* Filters */}
          <div className="drawer__section">
            <button
              className={`drawer__section-header ${activeSection === 'filters' ? 'drawer__section-header--active' : ''}`}
              onClick={() => toggle('filters')}
            >
              <span className="drawer__section-icon">⚙</span>
              <span>Filters</span>
              <span className="drawer__chevron">{activeSection === 'filters' ? '−' : '+'}</span>
            </button>
            {activeSection === 'filters' && (
              <div className="drawer__section-body">
                <FilterPanel communities={communities} onFilteredChange={onFilteredChange} />
              </div>
            )}
          </div>

          {/* Statistics */}
          <div className="drawer__section">
            <button
              className={`drawer__section-header ${activeSection === 'stats' ? 'drawer__section-header--active' : ''}`}
              onClick={() => toggle('stats')}
            >
              <span className="drawer__section-icon">📊</span>
              <span>Statistics</span>
              <span className="drawer__chevron">{activeSection === 'stats' ? '−' : '+'}</span>
            </button>
            {activeSection === 'stats' && (
              <div className="drawer__section-body">
                <StatsPanel />
              </div>
            )}
          </div>

          {/* Data Coverage */}
          <div className="drawer__section">
            <button
              className={`drawer__section-header ${activeSection === 'coverage' ? 'drawer__section-header--active' : ''}`}
              onClick={() => toggle('coverage')}
            >
              <span className="drawer__section-icon">📈</span>
              <span>Data Coverage</span>
              <span className="drawer__chevron">{activeSection === 'coverage' ? '−' : '+'}</span>
            </button>
            {activeSection === 'coverage' && (
              <div className="drawer__section-body">
                <CoverageDashboard onClose={() => setActiveSection(null)} />
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  )
}

export default ControlDrawer
