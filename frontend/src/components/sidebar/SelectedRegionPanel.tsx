import { useEffect, useRef, useState } from 'react';
import { RegionSummary, Season } from '../../api/catApi';
import { useResearchProfile } from '../../hooks/useResearchProfile';
import { exportResearchProfileReport } from '../../utils/reportExport';
import { DATA_UNAVAILABLE, formatResearchValue } from '../../utils/formatResearchValue';
import MetricTooltip from '../MetricTooltip';
import { formatMissing, formatStatus, statusClassName } from './sidebarUtils';

interface SelectedRegionPanelProps {
    region: RegionSummary | null;
    season: Season;
    focusKey?: number;
    pinned: boolean;
    pinDisabled: boolean;
    onTogglePin: (regionCode: string) => void;
}

function telehealthNeedLabel(score: number | null | undefined): string {
    if (score === null || score === undefined || !Number.isFinite(score)) {
        return DATA_UNAVAILABLE;
    }
    if (score <= 30) return `Low Need (${score.toFixed(1)})`;
    if (score <= 60) return `Moderate Need (${score.toFixed(1)})`;
    if (score <= 80) return `High Need (${score.toFixed(1)})`;
    return `Critical Need (${score.toFixed(1)})`;
}

export default function SelectedRegionPanel({
    region,
    season,
    focusKey = 0,
    pinned,
    pinDisabled,
    onTogglePin,
}: SelectedRegionPanelProps) {
    const { profile, loading, error } = useResearchProfile(region?.region_code ?? null, season);
    const panelRef = useRef<HTMLElement | null>(null);
    const [highlight, setHighlight] = useState(false);

    useEffect(() => {
        if (!region || focusKey === 0) return;
        panelRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        setHighlight(true);
        const timeout = window.setTimeout(() => setHighlight(false), 1400);
        return () => window.clearTimeout(timeout);
    }, [focusKey, region]);

    if (!region) {
        return null;
    }

    const handleDownloadReport = async () => {
        if (!profile) return;
        await exportResearchProfileReport(profile, document.querySelector('.leaflet-container'));
    };

    const handleCopyShareLink = async () => {
        await navigator.clipboard?.writeText(window.location.href);
    };

    return (
        <section
            ref={panelRef}
            className={`selected-region-panel ${highlight ? 'focused' : ''}`}
        >
            <div className="selected-region-header">
                <div>
                    <h2>{region.name}</h2>
                    <small>{region.region_code}</small>
                </div>
                <button
                    type="button"
                    className={`pin-button ${pinned ? 'pinned' : ''}`}
                    aria-label={`${pinned ? 'Unpin' : 'Pin'} ${region.name}`}
                    disabled={!pinned && pinDisabled}
                    onClick={() => onTogglePin(region.region_code)}
                >
                    {pinned ? 'Pinned' : 'Pin'}
                </button>
            </div>

            <div className="selected-region-actions">
                <button
                    type="button"
                    className="sidebar-action-button"
                    disabled={loading || !profile}
                    onClick={handleDownloadReport}
                >
                    Download Report
                </button>
                <button
                    type="button"
                    className="sidebar-action-button"
                    onClick={handleCopyShareLink}
                >
                    Copy Share Link
                </button>
            </div>

            {error && <div className="selected-region-note error">{error}</div>}
            {profile?.region.has_data_gap && (
                <div className="selected-region-note">
                    {profile.region.data_confidence} confidence · {profile.region.missing_fields.length} data gaps
                </div>
            )}

            <div className="selected-detail-grid">
                <span>
                    CAT tier
                    <MetricTooltip term="CAT Tier">
                        Transport access category. Higher tiers indicate more limited or fragile access.
                    </MetricTooltip>
                </span>
                <strong>{formatMissing(region.cat_tier)}</strong>

                <span>
                    Telehealth
                    <MetricTooltip term="Telehealth Status">
                        Combines affordability and clinic access into a practical access label.
                    </MetricTooltip>
                </span>
                <strong className={`status-text ${statusClassName(region.telehealth_status)}`}>
                    {formatStatus(region.telehealth_status)}
                </strong>

                <span>
                    Desert score
                    <MetricTooltip term="Healthcare Desert Score">
                        Higher scores mean greater need for telehealth due to healthcare access barriers.
                    </MetricTooltip>
                </span>
                <strong>{formatResearchValue(profile?.healthcare.desert_score ?? region.desert_score, { digits: 1 })}</strong>

                <span>
                    Telehealth need
                    <MetricTooltip term="Telehealth Need">
                        Interprets healthcare desert score: 0-30 low, 31-60 moderate, 61-80 high, and 81-100 critical.
                    </MetricTooltip>
                </span>
                <strong>{telehealthNeedLabel(profile?.healthcare.desert_score ?? region.desert_score)}</strong>

                <span>
                    Affordability
                    <MetricTooltip term="Affordability Burden">
                        Whether monthly internet cost is affordable relative to income data.
                    </MetricTooltip>
                </span>
                <strong>{formatStatus(profile?.affordability.status ?? region.affordability_status)}</strong>

                <span>
                    Data confidence
                    <MetricTooltip term="Data Confidence">
                        Confidence describes whether supporting coverage data is strong, weak, or missing.
                    </MetricTooltip>
                </span>
                <strong>{formatStatus(region.data_confidence)}</strong>

                <span>
                    Data gap
                    <MetricTooltip term="Data Incomplete">
                        Some required coverage, speed, affordability, or access evidence is missing.
                    </MetricTooltip>
                </span>
                <strong>{region.has_data_gap ? 'Data incomplete' : 'No gap flagged'}</strong>

                <span>Region</span>
                <strong>{formatMissing(region.region)}</strong>

                <span>Download speed</span>
                <strong>
                    {profile
                        ? formatResearchValue(profile.connectivity.ookla_download_mbps, { suffix: ' Mbps', digits: 1 })
                        : DATA_UNAVAILABLE}
                </strong>

                <span>Upload speed</span>
                <strong>
                    {profile
                        ? formatResearchValue(profile.connectivity.ookla_upload_mbps, { suffix: ' Mbps', digits: 1 })
                        : DATA_UNAVAILABLE}
                </strong>

                <span>Latency</span>
                <strong>
                    {profile
                        ? formatResearchValue(profile.connectivity.latency_ms, { suffix: ' ms', digits: 0 })
                        : DATA_UNAVAILABLE}
                </strong>

                <span>Cost burden</span>
                <strong>
                    {profile
                        ? formatResearchValue(profile.affordability.burden_pct, { suffix: '%', digits: 2 })
                        : DATA_UNAVAILABLE}
                </strong>

                <span>Nearest care</span>
                <strong>
                    {profile
                        ? formatResearchValue(profile.healthcare.nearest_facility_name)
                        : DATA_UNAVAILABLE}
                </strong>

                <span>Facility distance</span>
                <strong>
                    {profile
                        ? formatResearchValue(profile.healthcare.nearest_facility_distance_km, { suffix: ' km', digits: 1 })
                        : DATA_UNAVAILABLE}
                </strong>
            </div>
        </section>
    );
}
