/**
 * SegmentedControl — Compact segmented toggle.
 * Used for Season switching (Summer | Winter | Year-Round).
 */
import React from 'react'

const SegmentedControl = ({ options, value, onChange, size = 'default' }) => (
  <div className={`segmented-control segmented-control--${size}`}>
    {options.map(opt => (
      <button
        key={opt.value}
        className={`segment ${value === opt.value ? 'segment--active' : ''}`}
        onClick={() => onChange(opt.value)}
        title={opt.title || opt.label}
      >
        {opt.icon && <span className="segment__icon">{opt.icon}</span>}
        <span className="segment__label">{opt.label}</span>
      </button>
    ))}
  </div>
)

export default SegmentedControl
