import { RegionSummary } from '../../api/catApi';
import MetricTooltip from '../MetricTooltip';
import { formatMissing, formatStatus, statusClassName } from './sidebarUtils';

interface SelectedRegionPanelProps {
    region: RegionSummary | null;
    pinned: boolean;
    pinDisabled: boolean;
    onTogglePin: (regionCode: string) => void;
}

export default function SelectedRegionPanel({
    region,
    pinned,
    pinDisabled,
    onTogglePin,
}: SelectedRegionPanelProps) {
    if (!region) {
        return null;
    }

    return (
        <section className="selected-region-panel">
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
                <strong>{region.desert_score ?? 'Unknown'}</strong>

                <span>
                    Affordability
                    <MetricTooltip term="Affordability Burden">
                        Whether monthly internet cost is affordable relative to income data.
                    </MetricTooltip>
                </span>
                <strong>{formatStatus(region.affordability_status)}</strong>

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
            </div>
        </section>
    );
}
