import { RegionSummary } from '../../api/catApi';
import Button from '../ui/Button';
import StatusBadge from '../ui/StatusBadge';
import { getRegionSeverityClassName } from '../../domain/metrics';
import { getTelehealthStatusLabel, getTelehealthStatusTone } from '../../domain/statusPresentation';
import {
    formatMissing,
    formatStatus,
} from './sidebarUtils';

interface RegionCardProps {
    region: RegionSummary;
    selected: boolean;
    pinned: boolean;
    pinDisabled: boolean;
    showCatDetails?: boolean;
    showPin?: boolean;
    onSelect: (regionCode: string) => void;
    onTogglePin: (regionCode: string) => void;
}

export default function RegionCard({
    region,
    selected,
    pinned,
    pinDisabled,
    showCatDetails = true,
    showPin = true,
    onSelect,
    onTogglePin,
}: RegionCardProps) {
    const desertScore = region.desert_score === null || region.desert_score === undefined
        ? 'Unknown'
        : region.desert_score.toFixed(1);

    return (
        <article
            className={`region-card ${getRegionSeverityClassName(region)} ${selected ? 'selected' : ''}`}
            data-testid="sidebar-result"
            data-region-code={region.region_code}
        >
            <button
                type="button"
                className="region-card-main"
                onClick={() => onSelect(region.region_code)}
            >
                <span className="region-card-title">
                    <strong>{region.name}</strong>
                    <small>{region.region_code}</small>
                </span>
                <StatusBadge tone={getTelehealthStatusTone(region.telehealth_status)}>
                    {getTelehealthStatusLabel(region.telehealth_status)}
                </StatusBadge>
            </button>

            {showCatDetails && (
                <div className="region-card-metrics">
                    <span className="region-card-metric" aria-label={`Desert score ${desertScore}`}>
                        <small>Desert</small>
                        <strong>{desertScore}</strong>
                    </span>
                    <span className="region-card-metric">
                        <small>CAT tier</small>
                        <strong>{formatMissing(region.cat_tier)}</strong>
                    </span>
                    <span
                        className={`region-card-data-state${region.has_data_gap ? ' is-incomplete' : ''}`}
                        aria-label={`${region.has_data_gap ? 'Data incomplete' : 'Data complete'}. ${formatStatus(region.data_confidence)} confidence`}
                    >
                        <i aria-hidden="true" />
                        <span>
                            {region.has_data_gap ? 'Incomplete' : 'Complete'}
                            <small>{formatStatus(region.data_confidence)} confidence</small>
                        </span>
                    </span>
                </div>
            )}

            {showPin && (
                <Button
                    variant={pinned ? 'primary' : 'ghost'}
                    size="small"
                    className={`pin-button ${pinned ? 'pinned' : ''}`}
                    aria-label={`${pinned ? 'Unpin' : 'Pin'} ${region.name}`}
                    disabled={!pinned && pinDisabled}
                    onClick={() => onTogglePin(region.region_code)}
                >
                    {pinned ? 'Pinned' : 'Pin'}
                </Button>
            )}
        </article>
    );
}
