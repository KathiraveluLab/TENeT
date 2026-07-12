import { useEffect, useId, useMemo, useState } from 'react';
import { Season } from '../api/catApi';
import { useComparisonProfiles } from '../hooks/useComparisonProfiles';
import { ResearchProfile } from '../types/research';
import { DATA_UNAVAILABLE, formatResearchValue } from '../utils/formatResearchValue';
import Button from './ui/Button';
import './ResearchComparisonPanel.css';

interface ResearchComparisonPanelProps {
    pinnedRegionCodes: string[];
    season: Season;
    onSelectRegion: (regionCode: string) => void;
}

interface MetricConfig {
    key: string;
    label: string;
    higherIsBetter: boolean;
    getValue: (profile: ResearchProfile) => number | null;
    format: (value: number | null) => string;
}

const METRICS: MetricConfig[] = [
    {
        key: 'download',
        label: 'Download',
        higherIsBetter: true,
        getValue: profile => profile.connectivity.ookla_download_mbps,
        format: value => formatResearchValue(value, { suffix: ' Mbps', digits: 1 }),
    },
    {
        key: 'burden',
        label: 'Cost burden',
        higherIsBetter: false,
        getValue: profile => profile.affordability.burden_pct,
        format: value => formatResearchValue(value, { suffix: '%', digits: 2 }),
    },
    {
        key: 'desert',
        label: 'Desert score',
        higherIsBetter: false,
        getValue: profile => profile.healthcare.desert_score,
        format: value => formatResearchValue(value, { digits: 1 }),
    },
    {
        key: 'facilities',
        label: 'Facilities',
        higherIsBetter: true,
        getValue: profile => profile.healthcare.facility_count,
        format: value => formatResearchValue(value, { digits: 0 }),
    },
];

function metricAverage(values: Array<number | null>) {
    const numeric = values.filter((value): value is number => value !== null);
    if (!numeric.length) return null;
    return numeric.reduce((sum, value) => sum + value, 0) / numeric.length;
}

function badgeFor(value: number | null, values: Array<number | null>, higherIsBetter: boolean) {
    if (value === null) return null;
    const numeric = values.filter((item): item is number => item !== null);
    if (numeric.length < 2) return null;
    const best = higherIsBetter ? Math.max(...numeric) : Math.min(...numeric);
    const worst = higherIsBetter ? Math.min(...numeric) : Math.max(...numeric);
    if (best === worst) return null;
    if (value === best) return 'Best';
    if (value === worst) return 'Worst';
    return null;
}

export default function ResearchComparisonPanel({
    pinnedRegionCodes,
    season,
    onSelectRegion,
}: ResearchComparisonPanelProps) {
    const { profiles, missingCodes, loading, error } = useComparisonProfiles(pinnedRegionCodes, season);
    const [collapsed, setCollapsed] = useState(false);
    const [closed, setClosed] = useState(false);
    const bodyId = useId();
    const pinnedKey = useMemo(() => pinnedRegionCodes.join('|'), [pinnedRegionCodes]);

    useEffect(() => {
        setCollapsed(false);
        setClosed(false);
    }, [pinnedKey]);

    if (pinnedRegionCodes.length < 2) {
        return null;
    }

    if (closed) {
        return (
            <Button
                variant="secondary"
                size="small"
                className="research-comparison-reopen"
                data-testid="comparison-panel"
                onClick={() => {
                    setClosed(false);
                    setCollapsed(false);
                }}
            >
                Compare pinned communities
            </Button>
        );
    }

    return (
        <section
            className={`research-comparison-panel ${collapsed ? 'collapsed' : ''}`}
            data-testid="comparison-panel"
            aria-label="Pinned community comparison"
        >
            <div className="research-comparison-header">
                <div>
                    <h2>Community Comparison</h2>
                    <p>{profiles.length} pinned communities</p>
                </div>
                <div className="research-comparison-actions">
                    <Button
                        variant="ghost"
                        size="small"
                        onClick={() => setCollapsed(value => !value)}
                        aria-label={collapsed ? 'Expand comparison panel' : 'Collapse comparison panel'}
                        aria-expanded={!collapsed}
                        aria-controls={bodyId}
                    >
                        {collapsed ? 'Expand' : 'Collapse'}
                    </Button>
                    <Button
                        variant="ghost"
                        size="small"
                        onClick={() => setClosed(true)}
                        aria-label="Close comparison panel"
                    >
                        Close
                    </Button>
                </div>
            </div>

            {!collapsed && (
                <div className="research-comparison-body" id={bodyId}>
                    {loading && <div className="comparison-muted">Loading comparison...</div>}
                    {error && <div className="comparison-error">{error}</div>}
                    {!loading && missingCodes.length > 0 && (
                        <div className="comparison-muted">Missing: {missingCodes.join(', ')}</div>
                    )}

                    {!loading && !error && profiles.length >= 2 && (
                        <div className="comparison-table">
                            <div
                                className="comparison-grid comparison-grid-header"
                                style={{ gridTemplateColumns: `116px repeat(${profiles.length}, minmax(132px, 1fr))` }}
                            >
                                <span>Metric</span>
                                {profiles.map(profile => (
                                    <button
                                        type="button"
                                        key={profile.region.region_code}
                                        onClick={() => onSelectRegion(profile.region.region_code)}
                                        aria-label={`Select ${profile.region.name}`}
                                    >
                                        {profile.region.name}
                                    </button>
                                ))}
                            </div>

                            {METRICS.map(metric => {
                                const values = profiles.map(metric.getValue);
                                const average = metricAverage(values);
                                const max = Math.max(...values.filter((value): value is number => value !== null), 0);
                                return (
                                    <div
                                        className="comparison-grid"
                                        key={metric.key}
                                        style={{ gridTemplateColumns: `116px repeat(${profiles.length}, minmax(132px, 1fr))` }}
                                    >
                                        <span className="comparison-metric-label">{metric.label}</span>
                                        {profiles.map(profile => {
                                            const value = metric.getValue(profile);
                                            const badge = badgeFor(value, values, metric.higherIsBetter);
                                            const delta = value !== null && average !== null ? value - average : null;
                                            const barWidth = value !== null && max > 0 ? Math.max(6, (value / max) * 100) : 0;
                                            return (
                                                <div className="comparison-cell" key={profile.region.region_code}>
                                                    <div className="comparison-value-line">
                                                        <strong>{metric.format(value)}</strong>
                                                        {badge && <em className={`comparison-badge ${badge.toLowerCase()}`}>{badge}</em>}
                                                    </div>
                                                    <div className="comparison-bar-track">
                                                        <span style={{ width: `${barWidth}%` }} />
                                                    </div>
                                                    <small>
                                                        {delta === null
                                                            ? DATA_UNAVAILABLE
                                                            : `${delta >= 0 ? '+' : ''}${metric.format(delta)} vs group avg`}
                                                    </small>
                                                </div>
                                            );
                                        })}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}
        </section>
    );
}
