/**
 * ScenarioPanel – compact what-if controls floating above the map.
 *
 * Collapsed by default. Opened from a small "Scenarios" button.
 * Contains threshold sliders, preset selector, impact summary,
 * and a "Modeled Output" label.
 */
import React, { useCallback, useMemo, useState } from 'react';
import type { ScenarioState } from '../../hooks/useScenarioState';
import type { ScenarioPreviewState } from '../../hooks/useScenarioPreview';
import {
    BASELINE_THRESHOLDS,
    SCENARIO_PRESETS,
    type ScenarioThresholds,
} from '../../types/scenario';

/* ─── Styling ──────────────────────────────────────────────────────────── */

const PANEL_STYLE: React.CSSProperties = {
    position: 'relative',
    zIndex: 1,
    width: 340,
    maxHeight: 'calc(100vh - 170px)',
    overflowY: 'auto',
    background: 'rgba(15, 23, 42, 0.94)',
    backdropFilter: 'blur(16px)',
    WebkitBackdropFilter: 'blur(16px)',
    borderRadius: '14px',
    boxShadow: '0 8px 40px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(255,255,255,0.06)',
    padding: '20px',
    color: '#e2e8f0',
    fontFamily: "'Inter', -apple-system, sans-serif",
    fontSize: '13px',
    lineHeight: '1.5',
};

const HEADER_STYLE: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '14px',
};

const TITLE_STYLE: React.CSSProperties = {
    fontSize: '15px',
    fontWeight: 700,
    color: '#f1f5f9',
    letterSpacing: '-0.01em',
    margin: 0,
};

const BADGE_STYLE: React.CSSProperties = {
    display: 'inline-block',
    background: 'linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)',
    color: 'white',
    fontSize: '10px',
    fontWeight: 700,
    padding: '2px 7px',
    borderRadius: '4px',
    letterSpacing: '0.04em',
    textTransform: 'uppercase' as const,
};

const CLOSE_BTN_STYLE: React.CSSProperties = {
    appearance: 'none',
    border: 'none',
    background: 'rgba(255,255,255,0.08)',
    color: '#94a3b8',
    width: '28px',
    height: '28px',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '16px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'background 0.15s',
};

const DISCLAIMER_STYLE: React.CSSProperties = {
    fontSize: '11px',
    color: '#94a3b8',
    fontStyle: 'italic',
    lineHeight: 1.4,
    marginBottom: '16px',
    padding: '8px 10px',
    background: 'rgba(255,255,255,0.04)',
    borderRadius: '6px',
    borderLeft: '3px solid #7c3aed',
};

const SECTION_TITLE: React.CSSProperties = {
    fontSize: '11px',
    fontWeight: 600,
    color: '#94a3b8',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.06em',
    marginBottom: '8px',
    marginTop: '16px',
};

const SELECT_STYLE: React.CSSProperties = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: '8px',
    border: '1px solid rgba(255,255,255,0.1)',
    background: 'rgba(255,255,255,0.06)',
    color: '#e2e8f0',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
    outline: 'none',
};

const SLIDER_CONTAINER: React.CSSProperties = {
    marginBottom: '12px',
};

const SLIDER_LABEL: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '4px',
};

const SLIDER_NAME: React.CSSProperties = {
    fontSize: '12px',
    fontWeight: 500,
    color: '#cbd5e1',
};

const SLIDER_VALUE: React.CSSProperties = {
    fontSize: '12px',
    fontWeight: 700,
    color: '#7c3aed',
    fontVariantNumeric: 'tabular-nums',
};

const IMPACT_ROW: React.CSSProperties = {
    display: 'flex',
    gap: '6px',
    marginTop: '12px',
    flexWrap: 'wrap',
};

const IMPACT_CHIP: (color: string) => React.CSSProperties = (color) => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 10px',
    borderRadius: '20px',
    background: `${color}18`,
    border: `1px solid ${color}40`,
    fontSize: '12px',
    fontWeight: 600,
    color,
    fontVariantNumeric: 'tabular-nums',
});

const RESET_BTN: React.CSSProperties = {
    width: '100%',
    marginTop: '16px',
    padding: '9px 0',
    border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: '8px',
    background: 'rgba(255,255,255,0.05)',
    color: '#94a3b8',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s',
};

const IMPACT_NOTE: React.CSSProperties = {
    fontSize: '10px',
    color: '#64748b',
    fontStyle: 'italic',
    marginTop: '8px',
    lineHeight: 1.4,
};

const LOADING_STYLE: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 10px',
    background: 'rgba(124, 58, 237, 0.1)',
    borderRadius: '6px',
    fontSize: '12px',
    color: '#a78bfa',
    marginTop: '12px',
};

const ERROR_STYLE: React.CSSProperties = {
    padding: '8px 10px',
    background: 'rgba(239, 68, 68, 0.1)',
    borderRadius: '6px',
    fontSize: '12px',
    color: '#fca5a5',
    marginTop: '8px',
};

/* ─── Component ────────────────────────────────────────────────────────── */

interface ScenarioPanelProps {
    scenario: ScenarioState;
    preview: ScenarioPreviewState;
    gapModeActive: boolean;
}

export default function ScenarioPanel({
    scenario,
    preview,
    gapModeActive,
}: ScenarioPanelProps) {
    const { mode, thresholds, activePreset, setThreshold, applyPreset, resetToBaseline, deactivate } = scenario;
    const { data, loading, error } = preview;

    if (mode === 'off') return null;

    return (
        <div style={PANEL_STYLE} id="scenario-panel" data-testid="scenario-panel">
            {/* Header */}
            <div style={HEADER_STYLE}>
                <div>
                    <h3 style={TITLE_STYLE}>What-If Scenarios</h3>
                    <span style={{ ...BADGE_STYLE, marginTop: '4px' }}>Modeled Output</span>
                </div>
                <button
                    type="button"
                    style={CLOSE_BTN_STYLE}
                    onClick={deactivate}
                    aria-label="Close scenario panel"
                    title="Close scenario mode"
                >
                    ✕
                </button>
            </div>

            {/* Disclaimer */}
            <div style={DISCLAIMER_STYLE}>
                Scenario Mode shows modeled estimates based on selected thresholds.
                It does not represent observed ground truth and does not modify TENeT's baseline data.
            </div>

            {/* Gap Hunter note */}
            {gapModeActive && (
                <div style={{
                    ...DISCLAIMER_STYLE,
                    borderLeftColor: '#f59e0b',
                    background: 'rgba(245, 158, 11, 0.06)',
                }}>
                    Gap Hunter displays observed measurement data and is not affected by scenario thresholds.
                </div>
            )}

            {/* Preset */}
            <label
                style={{ ...SECTION_TITLE, display: 'block' }}
                htmlFor="scenario-preset-select"
            >
                Preset
            </label>
            <select
                style={SELECT_STYLE}
                value={activePreset ?? ''}
                onChange={e => {
                    const value = e.target.value;
                    if (value === 'baseline') {
                        resetToBaseline();
                    } else if (value) {
                        applyPreset(value);
                    }
                }}
                id="scenario-preset-select"
            >
                <option value="">Custom</option>
                {SCENARIO_PRESETS.map(preset => (
                    <option key={preset.id} value={preset.id}>{preset.label}</option>
                ))}
                <option value="baseline">Reset to Current Baseline</option>
            </select>

            {/* Broadband */}
            <div style={SECTION_TITLE}>Broadband</div>
            <ThresholdSlider
                label="Download"
                unit="Mbps"
                value={thresholds.min_download_mbps}
                min={1}
                max={200}
                step={1}
                onChange={v => setThreshold('min_download_mbps', v)}
            />
            <ThresholdSlider
                label="Upload"
                unit="Mbps"
                value={thresholds.min_upload_mbps}
                min={1}
                max={100}
                step={1}
                onChange={v => setThreshold('min_upload_mbps', v)}
            />

            {/* Clinic Proximity */}
            <div style={SECTION_TITLE}>Clinic Proximity</div>
            <div style={SLIDER_CONTAINER}>
                <div style={SLIDER_LABEL}>
                    <span style={SLIDER_NAME}>
                        {thresholds.clinic_proximity_km === null
                            ? 'Baseline road/water/air rules'
                            : `Override: ${thresholds.clinic_proximity_km} km`
                        }
                    </span>
                    {thresholds.clinic_proximity_km !== null && (
                        <button
                            type="button"
                            onClick={() => setThreshold('clinic_proximity_km', null)}
                            style={{
                                appearance: 'none',
                                border: 'none',
                                background: 'none',
                                color: '#7c3aed',
                                cursor: 'pointer',
                                fontSize: '11px',
                                fontWeight: 600,
                                padding: 0,
                            }}
                        >
                            Use baseline
                        </button>
                    )}
                </div>
                {thresholds.clinic_proximity_km !== null ? (
                    <input
                        type="range"
                        min={5}
                        max={200}
                        step={5}
                        value={thresholds.clinic_proximity_km}
                        onChange={e => setThreshold('clinic_proximity_km', Number(e.target.value))}
                        style={{ width: '100%', accentColor: '#7c3aed' }}
                        id="scenario-clinic-slider"
                    />
                ) : (
                    <button
                        type="button"
                        onClick={() => setThreshold('clinic_proximity_km', 25)}
                        style={{
                            ...RESET_BTN,
                            marginTop: '4px',
                            padding: '6px 0',
                            fontSize: '11px',
                        }}
                    >
                        Override with custom distance
                    </button>
                )}
            </div>

            {/* Affordability */}
            <div style={SECTION_TITLE}>Affordability</div>
            <ThresholdSlider
                label="Burden threshold"
                unit="%"
                value={thresholds.affordability_burden_pct}
                min={0.5}
                max={10}
                step={0.5}
                onChange={v => setThreshold('affordability_burden_pct', v)}
            />

            {/* Loading */}
            {loading && (
                <div style={LOADING_STYLE}>
                    <span style={{
                        width: '14px',
                        height: '14px',
                        border: '2px solid rgba(124,58,237,0.3)',
                        borderTopColor: '#7c3aed',
                        borderRadius: '50%',
                        animation: 'scenario-spin 0.6s linear infinite',
                        flexShrink: 0,
                    }} />
                    Calculating scenario…
                </div>
            )}

            {/* Error */}
            {error && <div style={ERROR_STYLE}>{error}</div>}

            {/* Impact Summary */}
            {data && !loading && (
                <>
                    <div style={SECTION_TITLE}>Impact Summary</div>
                    <div data-testid="scenario-summary">
                    <div style={IMPACT_ROW}>
                        <span style={IMPACT_CHIP('#f59e0b')}>
                            Changed {data.summary.status_changed_regions}
                        </span>
                        <span style={IMPACT_CHIP('#22c55e')}>
                            ▲ {data.summary.improved_count}
                        </span>
                        <span style={IMPACT_CHIP('#ef4444')}>
                            ▼ {data.summary.worsened_count}
                        </span>
                    </div>

                    {/* Status distribution */}
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr',
                        gap: '4px 12px',
                        marginTop: '10px',
                        fontSize: '12px',
                    }}>
                        <span style={{ color: '#94a3b8' }}>Telehealth Ready</span>
                        <strong style={{ color: '#22c55e', textAlign: 'right' }}>{data.summary.telehealth_ready}</strong>
                        <span style={{ color: '#94a3b8' }}>Community Anchor</span>
                        <strong style={{ color: '#f59e0b', textAlign: 'right' }}>{data.summary.community_anchor}</strong>
                        <span style={{ color: '#94a3b8' }}>Limited Telehealth</span>
                        <strong style={{ color: '#8b5cf6', textAlign: 'right' }}>{data.summary.limited_telehealth}</strong>
                        <span style={{ color: '#94a3b8' }}>Critical Gap</span>
                        <strong style={{ color: '#ef4444', textAlign: 'right' }}>{data.summary.critical_gap}</strong>
                        <span style={{ color: '#94a3b8' }}>Data Unavailable</span>
                        <strong style={{ color: '#6b7280', textAlign: 'right' }}>{data.summary.data_unavailable}</strong>
                    </div>

                    <div style={IMPACT_NOTE}>
                        These counts show how classifications would change under the selected assumptions.
                        They do not indicate actual measured changes in infrastructure or healthcare access.
                    </div>
                    </div>
                </>
            )}

            {/* Reset */}
            <button
                type="button"
                style={RESET_BTN}
                onClick={resetToBaseline}
                id="scenario-reset-button"
            >
                Reset to Baseline
            </button>

            {/* Spinner keyframes */}
            <style>{`
                @keyframes scenario-spin {
                    to { transform: rotate(360deg); }
                }
                #scenario-panel::-webkit-scrollbar {
                    width: 5px;
                }
                #scenario-panel::-webkit-scrollbar-track {
                    background: transparent;
                }
                #scenario-panel::-webkit-scrollbar-thumb {
                    background: rgba(255,255,255,0.1);
                    border-radius: 4px;
                }
                #scenario-panel input[type="range"] {
                    height: 4px;
                    border-radius: 2px;
                    -webkit-appearance: none;
                    appearance: none;
                    background: rgba(255,255,255,0.12);
                    outline: none;
                }
                #scenario-panel input[type="range"]::-webkit-slider-thumb {
                    -webkit-appearance: none;
                    width: 16px;
                    height: 16px;
                    border-radius: 50%;
                    background: #7c3aed;
                    border: 2px solid rgba(255,255,255,0.2);
                    cursor: pointer;
                    transition: transform 0.15s;
                }
                #scenario-panel input[type="range"]::-webkit-slider-thumb:hover {
                    transform: scale(1.15);
                }
                #scenario-reset-button:hover {
                    background: rgba(255,255,255,0.1) !important;
                    color: #e2e8f0 !important;
                }
            `}</style>
        </div>
    );
}

/* ─── Slider sub-component ─────────────────────────────────────────────── */

interface ThresholdSliderProps {
    label: string;
    unit: string;
    value: number;
    min: number;
    max: number;
    step: number;
    onChange: (value: number) => void;
}

function ThresholdSlider({ label, unit, value, min, max, step, onChange }: ThresholdSliderProps) {
    return (
        <div style={SLIDER_CONTAINER}>
            <div style={SLIDER_LABEL}>
                <span style={SLIDER_NAME}>{label}</span>
                <span style={SLIDER_VALUE}>{value} {unit}</span>
            </div>
            <input
                type="range"
                aria-label={`${label} threshold`}
                min={min}
                max={max}
                step={step}
                value={value}
                onChange={e => onChange(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#7c3aed' }}
            />
        </div>
    );
}
