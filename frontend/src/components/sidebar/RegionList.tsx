import { RegionSummary } from '../../api/catApi';
import RegionCard from './RegionCard';

interface RegionListProps {
    regions: RegionSummary[];
    selectedRegionCode: string | null;
    pinnedRegionCodes: string[];
    maxPinnedRegions: number;
    showCatDetails?: boolean;
    showPin?: boolean;
    onSelectRegion: (regionCode: string) => void;
    onTogglePin: (regionCode: string) => void;
}

export default function RegionList({
    regions,
    selectedRegionCode,
    pinnedRegionCodes,
    maxPinnedRegions,
    showCatDetails = true,
    showPin = true,
    onSelectRegion,
    onTogglePin,
}: RegionListProps) {
    if (!regions.length) {
        return (
            <div className="region-list-empty">
                No matching communities.
            </div>
        );
    }

    return (
        <div className="region-list">
            {regions.map(region => (
                <RegionCard
                    key={region.region_code}
                    region={region}
                    selected={region.region_code === selectedRegionCode}
                    pinned={pinnedRegionCodes.includes(region.region_code)}
                    pinDisabled={pinnedRegionCodes.length >= maxPinnedRegions}
                    showCatDetails={showCatDetails}
                    showPin={showPin}
                    onSelect={onSelectRegion}
                    onTogglePin={onTogglePin}
                />
            ))}
        </div>
    );
}
