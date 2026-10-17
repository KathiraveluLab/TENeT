import { useEffect, useRef, useState, type ReactNode } from 'react';
import { RegionSummary, Season } from '../../api/catApi';
import type { BaseMapLayer } from '../../domain/mapMode';
import type { ScenarioRegion } from '../../types/scenario';
import { useResearchProfile } from '../../hooks/useResearchProfile';
import { exportResearchProfileReport } from '../../utils/reportExport';
import {
    getTelehealthStatusClassName,
    getTelehealthStatusLabel,
    getTelehealthStatusTone,
} from '../../domain/statusPresentation';
import {
    formatMissing,
    formatStatus,
    telehealthNeedLabel,
} from './sidebarUtils';
import { DATA_UNAVAILABLE, formatResearchValue } from '../../utils/formatResearchValue';
import { ScenarioSidebarCard } from '../scenario/ScenarioLayer';
import MetricTooltip from '../MetricTooltip';
import Button from '../ui/Button';
import StatusBadge from '../ui/StatusBadge';

interface SelectedRegionPanelProps {
    region: RegionSummary | null;
    season: Season;
    focusKey?: number;
    activeLayer?: BaseMapLayer;
    pinned: boolean;
    pinDisabled: boolean;
    onTogglePin: (regionCode: string) => void;
    scenarioRegion?: ScenarioRegion;
}

export default function SelectedRegionPanel({
    region,
    season,
    focusKey = 0,
    activeLayer = 'cat',
    pinned,
    pinDisabled,
    onTogglePin,
    scenarioRegion,
}: SelectedRegionPanelProps) {
    const { profile, loading, error } = useResearchProfile(region?.region_code ?? null, season);
    const panelRef = useRef<HTMLElement | null>(null);
    const [highlight, setHighlight] = useState(false);
    const [actionStatus, setActionStatus] = useState<{ message: string; error: boolean } | null>(null);

    useEffect(() => {
        if (!region || focusKey === 0) return;
        panelRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        setHighlight(true);
        const timeout = window.setTimeout(() => setHighlight(false), 1400);
        return () => window.clearTimeout(timeout);
    }, [focusKey, region]);

    if (!region) {
        return (
            <section className="selected-region-panel selected-region-empty">
                <strong>Select a community</strong>
                <span>Choose a result to inspect access, connectivity, and data quality.</span>
            </section>
        );
    }

    const handleDownloadReport = async () => {
        if (!profile) return;
        try {
            await exportResearchProfileReport(
                profile,
                document.querySelector<HTMLElement>('.leaflet-container'),
            );
            setActionStatus({ message: 'Report download started.', error: false });
        } catch {
            setActionStatus({ message: 'Report could not be generated.', error: true });
        }
    };

    const handleCopyShareLink = async () => {
        try {
            if (!navigator.clipboard) throw new Error('Clipboard unavailable');
            await navigator.clipboard.writeText(window.location.href);
            setActionStatus({ message: 'Share link copied.', error: false });
        } catch {
            setActionStatus({ message: 'Share link could not be copied.', error: true });
        }
    };

    const profileFallback = loading
        ? 'Loading…'
        : error
            ? 'Details unavailable'
            : DATA_UNAVAILABLE;
    const catDetailSections = (
        <>
            <DetailSection title="CAT access">
                <DetailRow
                    label={<>CAT tier<MetricTooltip term="CAT Tier">Transport access category. Higher tiers indicate more limited or fragile access.</MetricTooltip></>}
                    value={formatMissing(region.cat_tier)}
                />
                <DetailRow
                    label={<>Healthcare desert score<MetricTooltip term="Healthcare Desert Score">Higher scores mean greater need for telehealth due to healthcare access barriers.</MetricTooltip></>}
                    value={formatResearchValue(profile?.healthcare.desert_score ?? region.desert_score, { digits: 1 })}
                />
                <DetailRow
                    label={<>Telehealth need<MetricTooltip term="Telehealth Need">Interprets healthcare desert score: below 25 adequate, 25-49 moderate, 50-74 high, and 75-100 critical.</MetricTooltip></>}
                    value={telehealthNeedLabel(profile?.healthcare.desert_score ?? region.desert_score)}
                />
                <DetailRow label="Region" value={formatMissing(region.region)} />
                <DetailRow label="Season" value={profile?.telehealth.season_note ?? formatStatus(season)} />
            </DetailSection>

            <DetailSection title="Transport evidence">
                <DetailRow
                    label={<>Telehealth status<MetricTooltip term="Telehealth Status">Combines affordability and clinic access into a practical access label.</MetricTooltip></>}
                    value={<span className={`status-text ${getTelehealthStatusClassName(region.telehealth_status)}`}>{getTelehealthStatusLabel(region.telehealth_status)}</span>}
                />
                <DetailRow label="Nearest care" value={profile ? formatResearchValue(profile.healthcare.nearest_facility_name) : profileFallback} />
                <DetailRow label="Facility distance" value={profile ? formatResearchValue(profile.healthcare.nearest_facility_distance_km, { suffix: ' km', digits: 1 }) : profileFallback} />
            </DetailSection>

            <DetailSection title="Data confidence">
                <DetailRow
                    label={<>Confidence<MetricTooltip term="Data Confidence">Confidence describes whether supporting coverage data is strong, weak, or missing.</MetricTooltip></>}
                    value={formatStatus(region.data_confidence)}
                />
                <DetailRow
                    label={<>Coverage<MetricTooltip term="Data Incomplete">Some required coverage, speed, affordability, or access evidence is missing.</MetricTooltip></>}
                    value={region.has_data_gap ? 'Data incomplete' : 'No gap flagged'}
                />
            </DetailSection>
        </>
    );
    const telehealthDetailSections = (
        <>
            <DetailSection title="Access">
                <DetailRow
                    label={<>CAT tier<MetricTooltip term="CAT Tier">Transport access category. Higher tiers indicate more limited or fragile access.</MetricTooltip></>}
                    value={formatMissing(region.cat_tier)}
                />
                <DetailRow
                    label={<>Telehealth<MetricTooltip term="Telehealth Status">Combines affordability and clinic access into a practical access label.</MetricTooltip></>}
                    value={<span className={`status-text ${getTelehealthStatusClassName(region.telehealth_status)}`}>{getTelehealthStatusLabel(region.telehealth_status)}</span>}
                />
                <DetailRow
                    label={<>Telehealth need<MetricTooltip term="Telehealth Need">Interprets healthcare desert score: below 25 adequate, 25-49 moderate, 50-74 high, and 75-100 critical.</MetricTooltip></>}
                    value={telehealthNeedLabel(profile?.healthcare.desert_score ?? region.desert_score)}
                />
                <DetailRow label="Region" value={formatMissing(region.region)} />
            </DetailSection>

            <DetailSection title="Connectivity">
                <DetailRow label="Download speed" value={profile ? formatResearchValue(profile.connectivity.ookla_download_mbps, { suffix: ' Mbps', digits: 1 }) : profileFallback} />
                <DetailRow label="Upload speed" value={profile ? formatResearchValue(profile.connectivity.ookla_upload_mbps, { suffix: ' Mbps', digits: 1 }) : profileFallback} />
                <DetailRow label="Latency" value={profile ? formatResearchValue(profile.connectivity.latency_ms, { suffix: ' ms', digits: 0 }) : profileFallback} />
            </DetailSection>

            <DetailSection title="Affordability">
                <DetailRow
                    label={<>Status<MetricTooltip term="Affordability Burden">Whether monthly internet cost is affordable relative to income data.</MetricTooltip></>}
                    value={formatStatus(profile?.affordability.status ?? region.affordability_status)}
                />
                <DetailRow label="Cost burden" value={profile ? formatResearchValue(profile.affordability.burden_pct, { suffix: '%', digits: 2 }) : profileFallback} />
            </DetailSection>

            <DetailSection title="Healthcare">
                <DetailRow
                    label={<>Desert score<MetricTooltip term="Healthcare Desert Score">Higher scores mean greater need for telehealth due to healthcare access barriers.</MetricTooltip></>}
                    value={formatResearchValue(profile?.healthcare.desert_score ?? region.desert_score, { digits: 1 })}
                />
                <DetailRow label="Nearest care" value={profile ? formatResearchValue(profile.healthcare.nearest_facility_name) : profileFallback} />
                <DetailRow label="Facility distance" value={profile ? formatResearchValue(profile.healthcare.nearest_facility_distance_km, { suffix: ' km', digits: 1 }) : profileFallback} />
            </DetailSection>

            <DetailSection title="Data confidence">
                <DetailRow
                    label={<>Confidence<MetricTooltip term="Data Confidence">Confidence describes whether supporting coverage data is strong, weak, or missing.</MetricTooltip></>}
                    value={formatStatus(region.data_confidence)}
                />
                <DetailRow
                    label={<>Coverage<MetricTooltip term="Data Incomplete">Some required coverage, speed, affordability, or access evidence is missing.</MetricTooltip></>}
                    value={region.has_data_gap ? 'Data incomplete' : 'No gap flagged'}
                />
            </DetailSection>
        </>
    );

    return (
        <section
            ref={panelRef}
            className={`selected-region-panel ${highlight ? 'focused' : ''}`}
        >
            <div className="selected-region-header">
                <div>
                    <h2>{region.name}</h2>
                    <small>{region.region_code} · {activeLayer === 'cat' ? 'CAT details' : activeLayer === 'affordability' ? 'Affordability details' : 'Gap Hunter details'}</small>
                </div>
                <Button
                    variant={pinned ? 'primary' : 'secondary'}
                    size="small"
                    className="selected-region-pin"
                    aria-label={`${pinned ? 'Unpin' : 'Pin'} ${region.name}`}
                    disabled={!pinned && pinDisabled}
                    onClick={() => onTogglePin(region.region_code)}
                >
                    {pinned ? 'Pinned' : 'Pin'}
                </Button>
            </div>

            {activeLayer !== 'affordability' ? (
                <div className="selected-region-summary" data-testid="cat-region-summary">
                    <StatusBadge tone="neutral" showDot>
                        CAT tier {formatMissing(region.cat_tier)}
                    </StatusBadge>
                    <span><small>Desert score</small><strong>{formatResearchValue(region.desert_score, { digits: 1 })}</strong></span>
                    <span><small>Region</small><strong>{formatMissing(region.region)}</strong></span>
                </div>
            ) : (
                <div className="selected-region-summary" data-testid="affordability-region-summary">
                    <StatusBadge tone={getTelehealthStatusTone(region.telehealth_status)} showDot>
                        {getTelehealthStatusLabel(region.telehealth_status)}
                    </StatusBadge>
                    <span><small>Affordability</small><strong>{formatStatus(profile?.affordability.status ?? region.affordability_status)}</strong></span>
                    <span><small>Cost burden</small><strong>{profile ? formatResearchValue(profile.affordability.burden_pct, { suffix: '%', digits: 2 }) : profileFallback}</strong></span>
                </div>
            )}

            <div className="selected-region-actions">
                <Button
                    variant="primary"
                    size="small"
                    data-testid="download-report"
                    disabled={loading || !profile}
                    onClick={handleDownloadReport}
                    aria-label={`Download report for ${region.name}`}
                >
                    Download Report
                </Button>
                <Button
                    variant="secondary"
                    size="small"
                    data-testid="copy-share-link"
                    onClick={handleCopyShareLink}
                    aria-label={`Copy share link for ${region.name}`}
                >
                    Copy Share Link
                </Button>
            </div>

            {actionStatus && (
                <div
                    className={`selected-region-action-status${actionStatus.error ? ' is-error' : ''}`}
                    role={actionStatus.error ? 'alert' : 'status'}
                >
                    {actionStatus.message}
                </div>
            )}

            {loading && <div className="selected-region-note" role="status">Loading community details…</div>}
            {error && <div className="selected-region-note error" role="alert">Community details unavailable: {error}</div>}
            {profile?.region?.has_data_gap && (
                <div className="selected-region-note" role="status">
                    {profile.region?.data_confidence ?? DATA_UNAVAILABLE} confidence · {profile.region?.missing_fields?.length ?? 0} data gaps
                </div>
            )}

            <div className="selected-region-detail-sections">
                {activeLayer === 'affordability' ? telehealthDetailSections : catDetailSections}
            </div>

            {/* Scenario Sidebar Card */}
            <ScenarioSidebarCard region={scenarioRegion} />
        </section>
    );
}

function DetailSection({ title, children }: { title: string; children: ReactNode }) {
    return (
        <section className="selected-detail-section">
            <h3>{title}</h3>
            <div className="selected-detail-grid">{children}</div>
        </section>
    );
}

function DetailRow({ label, value }: { label: ReactNode; value: ReactNode }) {
    return (
        <>
            <span>{label}</span>
            <strong>{value}</strong>
        </>
    );
}
