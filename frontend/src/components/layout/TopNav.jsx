/**
 * TopNav — Sticky top navigation bar.
 *
 * Contains: logo, layer pills, season segmented control,
 * search bar (center), export button (right).
 */
import React from 'react'
import PillGroup from '../ui/PillGroup'
import SegmentedControl from '../ui/SegmentedControl'
import SearchBar from '../SearchBar'
import ReportButton from '../ReportButton'

const LAYER_OPTIONS = [
  { value: 'digital_equity', label: 'Digital Equity' },
  { value: 'value_index',    label: 'Value Index' },
  { value: 'access_tier',    label: 'Access Tier' },
]

const SEASON_OPTIONS = [
  { value: 'summer',     label: 'Summer',     icon: '☀️' },
  { value: 'winter',     label: 'Winter',     icon: '❄️' },
  { value: 'year_round', label: 'Year-Round', icon: '🔄' },
]

const TopNav = ({
  vizMode, onVizModeChange,
  season, onSeasonChange,
  onSearch, onClearSearch, onCommunitySelect,
}) => (
  <nav className="topnav">
    {/* Left: Logo */}
    <div className="topnav__brand">
      <span className="topnav__logo">TENeT</span>
      <span className="topnav__subtitle">Telehealth Network Tool — Alaska</span>
    </div>

    {/* Center: Layer pills + Season + Search */}
    <div className="topnav__center">
      <PillGroup options={LAYER_OPTIONS} value={vizMode} onChange={onVizModeChange} />

      <div className="topnav__divider" />

      <SegmentedControl
        options={SEASON_OPTIONS}
        value={season}
        onChange={onSeasonChange}
        size="small"
      />

      <div className="topnav__divider" />

      <div className="topnav__search">
        <SearchBar
          onSearch={onSearch}
          onClear={onClearSearch}
          onCommunitySelect={onCommunitySelect}
        />
      </div>
    </div>

    {/* Right: Export */}
    <div className="topnav__actions">
      <ReportButton />
    </div>
  </nav>
)

export default TopNav
