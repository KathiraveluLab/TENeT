/**
 * ScenarioPanel – compact what-if controls floating above the map.
 *
 * Collapsed by default. Opened from a small "Scenarios" button.
 * Contains threshold sliders, preset selector, impact summary,
 * and a "Modeled Output" label.
 */
import type { ScenarioState } from '../../hooks/useScenarioState';
import type { ScenarioPreviewState } from '../../hooks/useScenarioPreview';
import { SCENARIO_PRESETS } from '../../types/scenario';
import { getTelehealthStatusLabel } from '../../domain/statusPresentation';
import Button from '../ui/Button';
import IconButton from '../ui/IconButton';
import './ScenarioPanel.css';

/* ─── Component ────────────────────────────────────────────────────────── */

interface ScenarioPanelProps {
    scenario: ScenarioState;
    preview: ScenarioPreviewState;
    onClose: () => void;
}

export default function ScenarioPanel({
    scenario,
    preview,
    onClose,
}: ScenarioPanelProps) {
    const { mode, thresholds, activePreset, setThreshold, applyPreset, resetToBaseline } = scenario;
    const { data, loading, error } = preview;
    const closePanel = () => {
        onClose();
        window.requestAnimationFrame(() => {
            document.getElementById('scenario-toggle-button')?.focus();
        });
    };

    if (mode === 'off') return null;

    return (
        <div className="scenario-panel" id="scenario-panel" data-testid="scenario-panel">
            {/* Header */}
            <div className="scenario-panel__header">
                <div>
                    <h3 className="scenario-panel__title">What-If Scenarios</h3>
                    <span className="scenario-panel__badge">Modeled Output</span>
                </div>
                <IconButton
                    icon="×"
                    size="small"
                    onClick={closePanel}
                    aria-label="Close scenario panel"
                    title="Close scenario mode"
                />
            </div>

            {/* Disclaimer */}
            <div className="scenario-panel__disclaimer">
                Scenario Mode shows modeled estimates based on selected thresholds.
                It does not represent observed ground truth and does not modify TENeT's baseline data.
            </div>

            {/* Preset */}
            <label
                className="scenario-panel__section-title"
                style={{ display: 'block' }}
                htmlFor="scenario-preset-select"
            >
                Preset
            </label>
            <select
                className="scenario-panel__select"
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
            <div className="scenario-panel__section-title">Broadband</div>
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
            <div className="scenario-panel__section-title">Clinic Proximity</div>
            <div className="scenario-panel__slider-group">
                <div className="scenario-panel__slider-header">
                    <span className="scenario-panel__slider-name">
                        {thresholds.clinic_proximity_km === null
                            ? 'Baseline road/water/air rules'
                            : `Override: ${thresholds.clinic_proximity_km} km`
                        }
                    </span>
                    {thresholds.clinic_proximity_km !== null && (
                        <Button
                            variant="ghost"
                            size="small"
                            className="scenario-panel__use-baseline"
                            onClick={() => setThreshold('clinic_proximity_km', null)}
                        >
                            Use baseline
                        </Button>
                    )}
                </div>
                {thresholds.clinic_proximity_km !== null ? (
                    <input
                        type="range"
                        aria-label="Clinic proximity threshold"
                        min={5}
                        max={200}
                        step={5}
                        value={thresholds.clinic_proximity_km}
                        onChange={e => setThreshold('clinic_proximity_km', Number(e.target.value))}
                        style={{ width: '100%', accentColor: '#7c3aed' }}
                        id="scenario-clinic-slider"
                    />
                ) : (
                    <Button
                        variant="secondary"
                        size="small"
                        style={{ width: '100%', marginTop: '4px' }}
                        onClick={() => setThreshold('clinic_proximity_km', 25)}
                    >
                        Override with custom distance
                    </Button>
                )}
            </div>

            {/* Affordability */}
            <div className="scenario-panel__section-title">Affordability</div>
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
                <div className="scenario-panel__loading" role="status">
                    <span className="scenario-panel__spinner" aria-hidden="true" />
                    Calculating scenario…
                </div>
            )}

            {/* Error */}
            {error && <div className="scenario-panel__error" role="alert">{error}</div>}

            {/* Impact Summary */}
            {data && !loading && (
                <>
                    <div className="scenario-panel__section-title">Impact Summary</div>
                    <div data-testid="scenario-summary">
                    <div className="scenario-panel__impact-row">
                        <span
                            className="scenario-panel__impact-chip"
                            style={{ background: '#f59e0b18', border: '1px solid #f59e0b40', color: '#f59e0b' }}
                        >
                            Changed {data.summary.status_changed_regions}
                        </span>
                        <span
                            className="scenario-panel__impact-chip"
                            style={{ background: '#15803d18', border: '1px solid #15803d40', color: '#15803d' }}
                        >
                            Improved ▲ {data.summary.improved_count}
                        </span>
                        <span
                            className="scenario-panel__impact-chip"
                            style={{ background: '#b4231818', border: '1px solid #b4231840', color: '#b42318' }}
                        >
                            Worsened ▼ {data.summary.worsened_count}
                        </span>
                    </div>

                    {/* Status distribution */}
                    <div className="scenario-panel__status-grid">
                        <span>{getTelehealthStatusLabel('TELEHEALTH_READY')}</span>
                        <strong style={{ color: 'var(--color-status-ready)' }}>{data.summary.telehealth_ready}</strong>
                        <span>{getTelehealthStatusLabel('COMMUNITY_ANCHOR')}</span>
                        <strong style={{ color: 'var(--color-status-anchor)' }}>{data.summary.community_anchor}</strong>
                        <span>{getTelehealthStatusLabel('LIMITED_TELEHEALTH')}</span>
                        <strong style={{ color: 'var(--color-status-limited)' }}>{data.summary.limited_telehealth}</strong>
                        <span>{getTelehealthStatusLabel('CRITICAL_GAP')}</span>
                        <strong style={{ color: 'var(--color-status-gap)' }}>{data.summary.critical_gap}</strong>
                        <span>{getTelehealthStatusLabel('DATA_UNAVAILABLE')}</span>
                        <strong style={{ color: 'var(--color-status-unknown)' }}>{data.summary.data_unavailable}</strong>
                    </div>

                    <div className="scenario-panel__impact-note">
                        These counts show how classifications would change under the selected assumptions.
                        They do not indicate actual measured changes in infrastructure or healthcare access.
                    </div>
                    </div>
                </>
            )}

            {/* Reset */}
            <Button
                variant="secondary"
                size="small"
                style={{ width: '100%', marginTop: '16px' }}
                onClick={resetToBaseline}
                id="scenario-reset-button"
            >
                Reset to Baseline
            </Button>
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
        <div className="scenario-panel__slider-group">
            <div className="scenario-panel__slider-header">
                <span className="scenario-panel__slider-name">{label}</span>
                <span className="scenario-panel__slider-value">{value} {unit}</span>
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
