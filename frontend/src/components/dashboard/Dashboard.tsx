import { useEffect, useRef, type ReactNode } from 'react';
import { useDashboardData, type DashboardSection } from '../../hooks/useDashboardData';
import Button from '../ui/Button';
import MetricCard from '../ui/MetricCard';
import Panel from '../ui/Panel';
import StatusBadge from '../ui/StatusBadge';
import { SATELLITE_PRIMARY_METRIC } from '../../domain/metrics';
import { getTelehealthStatusLabel } from '../../domain/statusPresentation';
import type { BaseMapLayer } from '../../domain/mapMode';
import './Dashboard.css';

export type InsightsMapLayer = BaseMapLayer;

interface DashboardProps {
    onClose: () => void;
    onViewMap?: (layer: InsightsMapLayer) => void;
    onViewRegion?: (regionCode: string) => void;
}

const SECTION_LABELS: Record<DashboardSection, string> = {
    statistics: 'statewide totals',
    telehealthStatus: 'telehealth status',
    healthcare: 'healthcare infrastructure',
    performance: 'network performance',
    dataGaps: 'data quality',
    affordability: 'affordability',
};

function displayNumber(value: number | null | undefined, digits = 0): string {
    if (value === null || value === undefined || !Number.isFinite(value)) return '—';
    return value.toLocaleString(undefined, {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    });
}

function percentage(value: number | null | undefined, digits = 0): string {
    return value === null || value === undefined || !Number.isFinite(value)
        ? '—'
        : `${displayNumber(value, digits)}%`;
}

function ratioPercent(value: number | null | undefined, total: number | null | undefined): number | null {
    if (value === null || value === undefined || !total) return null;
    return (value / total) * 100;
}

export default function Dashboard({ onClose, onViewMap, onViewRegion }: DashboardProps) {
    const titleRef = useRef<HTMLHeadingElement>(null);
    const {
        data,
        loading,
        error,
        sectionErrors,
        hasPartialData,
        availableSectionCount,
    } = useDashboardData();

    useEffect(() => {
        if (!loading) titleRef.current?.focus();
    }, [loading]);

    const viewMap = (layer: InsightsMapLayer = 'cat') => {
        if (onViewMap) onViewMap(layer);
        else onClose();
    };

    if (loading) {
        return (
            <div className="insights-state-shell">
                <Panel elevated className="insights-state-card" role="status">
                    <span className="insights-spinner" aria-hidden="true" />
                    <h1>Preparing Statewide Insights</h1>
                    <p>Combining telehealth, network, healthcare, and data-quality summaries.</p>
                    <Button variant="secondary" onClick={onClose}>View map</Button>
                </Panel>
            </div>
        );
    }

    if (error && availableSectionCount === 0) {
        return (
            <div className="insights-state-shell">
                <Panel elevated className="insights-state-card insights-state-card--error" role="alert">
                    <StatusBadge tone="critical">Insights unavailable</StatusBadge>
                    <h1 ref={titleRef} tabIndex={-1}>Statewide data could not be loaded</h1>
                    <p>{error}</p>
                    <Button variant="primary" onClick={onClose}>Return to map</Button>
                </Panel>
            </div>
        );
    }

    const { statistics, telehealthStatus, healthcare, performance, dataGaps, affordability } = data;
    const totalCommunities = telehealthStatus?.count ?? null;
    const criticalCount = telehealthStatus?.summary.critical_gap;
    const readyCount = telehealthStatus?.summary.telehealth_ready;
    const criticalRegions = telehealthStatus?.regions
        .filter(region => region.status === 'CRITICAL_GAP')
        .slice(0, 5) ?? [];
    const speedDistribution = performance?.distribution;
    const speedTileCount = speedDistribution
        ? Object.values(speedDistribution).reduce((sum, count) => sum + count, 0)
        : 0;
    const unavailableSections = (Object.keys(sectionErrors) as DashboardSection[])
        .map(section => SECTION_LABELS[section]);

    return (
        <div className="insights-page">
            <header className="insights-header">
                <div>
                    <span className="insights-eyebrow">TENeT statewide view</span>
                    <h1 ref={titleRef} tabIndex={-1}>Statewide Insights</h1>
                    <p>Prioritize telehealth gaps, validate evidence quality, and move directly back to the map.</p>
                </div>
                <Button variant="primary" onClick={onClose}>View map</Button>
            </header>

            <main className="insights-content">
                {hasPartialData && (
                    <div className="insights-partial-notice" role="status">
                        <StatusBadge tone="anchor">Partial data</StatusBadge>
                        <span>
                            Showing available statewide results. Unavailable sections: {unavailableSections.join(', ')}.
                        </span>
                    </div>
                )}

                <section className="insights-overview" aria-labelledby="statewide-overview-title">
                    <div className="insights-section-heading">
                        <div>
                            <span className="insights-eyebrow">At a glance</span>
                            <h2 id="statewide-overview-title">Statewide operating picture</h2>
                        </div>
                        <span className="insights-source-note">Counts reflect the latest available source for each section.</span>
                    </div>
                    <div className="insights-metric-grid">
                        <MetricCard
                            label="Communities classified"
                            value={displayNumber(totalCommunities)}
                            supportingText="Communities in the telehealth status dataset"
                            tone="info"
                        />
                        <MetricCard
                            label="Critical telehealth gaps"
                            value={displayNumber(criticalCount)}
                            supportingText={criticalCount === undefined
                                ? 'Telehealth classification unavailable'
                                : `${percentage(ratioPercent(criticalCount, totalCommunities), 1)} of classified communities`}
                            tone="danger"
                        />
                        <MetricCard
                            label="Telehealth ready"
                            value={displayNumber(readyCount)}
                            supportingText={readyCount === undefined
                                ? 'Telehealth classification unavailable'
                                : `${percentage(ratioPercent(readyCount, totalCommunities), 1)} of classified communities`}
                            tone="success"
                        />
                        <MetricCard
                            label="Broadband places with data gaps"
                            value={displayNumber(dataGaps?.places_with_gaps)}
                            supportingText={dataGaps
                                ? `${percentage(ratioPercent(dataGaps.places_with_gaps, dataGaps.total_places), 1)} of ${displayNumber(dataGaps.total_places)} evaluated places`
                                : 'Data-quality summary unavailable'}
                            tone="warning"
                        />
                    </div>
                </section>

                <Panel className="insights-panel insights-panel--critical" elevated>
                    <SectionHeading
                        eyebrow="Action queue"
                        title="Critical telehealth gaps"
                        description="Communities classified with affordability constraints and insufficient nearby care support."
                        action={<Button size="small" onClick={() => viewMap('cat')}>View CAT map</Button>}
                    />

                    {!telehealthStatus ? (
                        <SectionUnavailable message={sectionErrors.telehealthStatus} />
                    ) : criticalRegions.length === 0 ? (
                        <div className="insights-empty-state">No critical-gap communities are present in the current statewide classification.</div>
                    ) : (
                        <div className="insights-priority-list">
                            {criticalRegions.map(region => (
                                <article key={region.region_code} className="insights-priority-row">
                                    <div className="insights-priority-main">
                                        <div>
                                            <strong>{region.region_name}</strong>
                                            <span>{region.region_code}</span>
                                        </div>
                                        <StatusBadge tone="critical">{getTelehealthStatusLabel('CRITICAL_GAP')}</StatusBadge>
                                    </div>
                                    <p>{region.recommendation || 'Review connectivity, affordability, and nearby clinic access on the map.'}</p>
                                    <Button
                                        size="small"
                                        variant="ghost"
                                        onClick={() => onViewRegion ? onViewRegion(region.region_code) : viewMap('cat')}
                                    >
                                        View on map
                                    </Button>
                                </article>
                            ))}
                            {(telehealthStatus.summary.critical_gap ?? 0) > criticalRegions.length && (
                                <div className="insights-list-note">
                                    Showing 5 of {displayNumber(telehealthStatus.summary.critical_gap)} critical communities.
                                </div>
                            )}
                        </div>
                    )}
                </Panel>

                <div className="insights-grid">
                    <Panel className="insights-panel">
                        <SectionHeading
                            eyebrow="Connectivity"
                            title="Network performance summary"
                            description="Observed Ookla measurements indicate whether current service can support reliable telehealth."
                            action={<Button size="small" onClick={() => viewMap('gap')}>Open Gap Hunter</Button>}
                        />
                        {!performance || !performance.has_data ? (
                            <SectionUnavailable message={sectionErrors.performance || 'No measured network-performance period is available.'} />
                        ) : (
                            <>
                                <div className="insights-inline-metrics">
                                    <MetricCard
                                        label="Average download"
                                        value={performance.speeds.avg_download_mbps === null
                                            ? 'Data unavailable'
                                            : `${displayNumber(performance.speeds.avg_download_mbps, 1)} Mbps`}
                                        supportingText={performance.period.label}
                                        tone="info"
                                    />
                                    <MetricCard
                                        label="Telehealth-viable tiles"
                                        value={percentage(performance.telehealth_viable_pct, 1)}
                                        supportingText={`${displayNumber(performance.coverage.tiles_with_speed_data)} tiles with speed data`}
                                        tone="success"
                                    />
                                </div>
                                <div className="insights-distribution" aria-label="Speed distribution by measured tile">
                                    <div className="insights-distribution__bar">
                                        {speedDistribution && Object.entries(speedDistribution).map(([level, count]) => (
                                            <span
                                                key={level}
                                                className={`is-${level}`}
                                                style={{ flexGrow: count }}
                                                title={`${level}: ${count} tiles`}
                                            />
                                        ))}
                                    </div>
                                    <div className="insights-distribution__legend">
                                        {speedDistribution && Object.entries(speedDistribution).map(([level, count]) => (
                                            <span key={level}><i className={`is-${level}`} />{level} {displayNumber(count)}</span>
                                        ))}
                                    </div>
                                    <small>Distribution across {displayNumber(speedTileCount)} measured tiles.</small>
                                </div>
                            </>
                        )}
                    </Panel>

                    <Panel className="insights-panel">
                        <SectionHeading
                            eyebrow="Care access"
                            title="Healthcare infrastructure"
                            description="Facility inventory helps identify where telehealth must supplement limited physical access."
                            action={<Button size="small" onClick={() => viewMap('cat')}>View communities</Button>}
                        />
                        {!healthcare ? (
                            <SectionUnavailable message={sectionErrors.healthcare} />
                        ) : (
                            <div className="insights-summary-list">
                                <SummaryRow label="Total facilities" value={displayNumber(healthcare.total_facilities)} strong />
                                <SummaryRow label="Hospitals" value={displayNumber(healthcare.by_type.hospital)} />
                                <SummaryRow label="Clinics" value={displayNumber(healthcare.by_type.clinic)} />
                                <SummaryRow label="Health centers" value={displayNumber(healthcare.by_type.health_center)} />
                                <SummaryRow label="Emergency services" value={displayNumber(healthcare.features.with_emergency)} />
                                <SummaryRow label="Telehealth-capable facilities" value={displayNumber(healthcare.features.with_telehealth)} />
                                <small>Source: {healthcare.data_source || 'Healthcare facility inventory'}</small>
                            </div>
                        )}
                    </Panel>

                    <Panel className="insights-panel">
                        <SectionHeading
                            eyebrow="Evidence risk"
                            title="Data quality risks"
                            description="Incomplete or low-confidence evidence should trigger verification before funding or service decisions."
                        />
                        {!dataGaps ? (
                            <SectionUnavailable message={sectionErrors.dataGaps} />
                        ) : (
                            <>
                                <div className="insights-inline-metrics insights-inline-metrics--four">
                                    <MetricCard label="Places with gaps" value={displayNumber(dataGaps.places_with_gaps)} tone="warning" />
                                    <MetricCard label="Low confidence" value={displayNumber(dataGaps.confidence_distribution.LOW)} tone="danger" />
                                    <MetricCard label="Viability uncertain" value={displayNumber(dataGaps.telehealth_viability.UNCERTAIN)} tone="warning" />
                                    <MetricCard label="Stored data points" value={displayNumber(statistics?.total_data_points)} tone="neutral" />
                                </div>
                                <div className="insights-callout">
                                    <div>
                                        <strong>{displayNumber(dataGaps.primary_access.SATELLITE)}</strong>
                                        <span>{SATELLITE_PRIMARY_METRIC.label}</span>
                                    </div>
                                    <p>{SATELLITE_PRIMARY_METRIC.description}</p>
                                </div>
                            </>
                        )}
                    </Panel>

                    <Panel className="insights-panel">
                        <SectionHeading
                            eyebrow="Household burden"
                            title="Affordability summary"
                            description="Income-based burden estimates identify analyzed zones where the modeled monthly internet cost exceeds the configured threshold."
                            action={<Button size="small" onClick={() => viewMap('affordability')}>Open telehealth access map</Button>}
                        />
                        {!affordability ? (
                            <SectionUnavailable message={sectionErrors.affordability} />
                        ) : (
                            <>
                                <div className="insights-inline-metrics">
                                    <MetricCard
                                        label="Unaffordable analyzed zones"
                                        value={displayNumber(affordability.summary.unaffordable)}
                                        supportingText={`of ${displayNumber(affordability.count)} analyzed ZCTAs`}
                                        tone="danger"
                                    />
                                    <MetricCard
                                        label="Affordable share"
                                        value={percentage(affordability.summary.affordable_pct, 1)}
                                        supportingText={`${displayNumber(affordability.summary.affordable)} analyzed zones`}
                                        tone="success"
                                    />
                                </div>
                                <div className="insights-method-note">
                                    Modeled at {`$${displayNumber(affordability.monthly_cost)}`} per month with a {percentage(affordability.threshold_pct, 1)} income-burden threshold. Zones without usable income data may be excluded.
                                </div>
                            </>
                        )}
                    </Panel>
                </div>
            </main>
        </div>
    );
}

function SectionHeading({
    eyebrow,
    title,
    description,
    action,
}: {
    eyebrow: string;
    title: string;
    description: string;
    action?: ReactNode;
}) {
    return (
        <div className="insights-panel__header">
            <div>
                <span className="insights-eyebrow">{eyebrow}</span>
                <h2>{title}</h2>
                <p>{description}</p>
            </div>
            {action && <div className="insights-panel__action">{action}</div>}
        </div>
    );
}

function SectionUnavailable({ message }: { message?: string }) {
    return (
        <div className="insights-unavailable" role="status">
            <StatusBadge tone="neutral">Unavailable</StatusBadge>
            <span>{message || 'This source did not return statewide data.'}</span>
        </div>
    );
}

function SummaryRow({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
    return (
        <div className={`insights-summary-row${strong ? ' is-strong' : ''}`}>
            <span>{label}</span>
            <strong>{value}</strong>
        </div>
    );
}
