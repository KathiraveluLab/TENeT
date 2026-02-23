/**
 * PillGroup — Horizontal pill-style toggle group.
 * Used for layer switching (Digital Equity / Value Index / Access Tier).
 */
import React from 'react'

const PillGroup = ({ options, value, onChange }) => (
  <div className="pill-group">
    {options.map(opt => (
      <button
        key={opt.value}
        className={`pill ${value === opt.value ? 'pill--active' : ''}`}
        onClick={() => onChange(opt.value)}
      >
        {opt.label}
      </button>
    ))}
  </div>
)

export default PillGroup
