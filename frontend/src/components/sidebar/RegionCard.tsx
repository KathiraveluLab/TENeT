import { RegionSummary } from '../../api/catApi';
import { formatMissing, formatStatus, statusClassName } from './sidebarUtils';

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
            className={`region-card ${selected ? 'selected' : ''}`}
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
                <span className={`status-badge ${statusClassName(region.telehealth_status)}`}>
                    {formatStatus(region.telehealth_status)}
                </span>
            </button>

            {showCatDetails && (
                <div className="region-card-meta">
                    <span>CAT {formatMissing(region.cat_tier)}</span>
                    <span>Desert {desertScore}</span>
                    <span>Confidence {formatStatus(region.data_confidence)}</span>
                    <span>{region.has_data_gap ? 'Data incomplete' : 'Data complete'}</span>
                </div>
            )}

            {showPin && (
                <button
                    type="button"
                    className={`pin-button ${pinned ? 'pinned' : ''}`}
                    aria-label={`${pinned ? 'Unpin' : 'Pin'} ${region.name}`}
                    disabled={!pinned && pinDisabled}
                    onClick={() => onTogglePin(region.region_code)}
                >
                    {pinned ? 'Pinned' : 'Pin'}
                </button>
            )}
        </article>
    );
}
