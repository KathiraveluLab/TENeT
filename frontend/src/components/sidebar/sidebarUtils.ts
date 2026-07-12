import type { RegionSummary, TelehealthStatusName } from '../../api/catApi';
import {
    getDesertScorePresentation,
    matchesDesertScoreFilter,
    type CatTier,
    type DesertScoreFilter,
} from '../../domain/metrics';

export type RegionSortMode = 'name' | 'tier' | 'desert';
export type DataGapFilter = 'all' | 'missing' | 'complete';

export interface SidebarFilters {
    tier: '' | `${CatTier}`;
    status: '' | TelehealthStatusName;
    desert: DesertScoreFilter;
    dataGap: DataGapFilter;
}

export function formatMissing(value: string | number | null | undefined, fallback = 'Unknown') {
    if (value === null || value === undefined || value === '') {
        return fallback;
    }
    return value;
}

export function formatStatus(status: string | null | undefined, fallback = 'Unknown') {
    if (!status) {
        return fallback;
    }
    return status
        .toLowerCase()
        .split('_')
        .map(part => part.charAt(0).toUpperCase() + part.slice(1))
        .join(' ');
}

export function telehealthNeedLabel(score: number | null | undefined): string {
    if (score === null || score === undefined || !Number.isFinite(score)) {
        return 'Data unavailable';
    }
    return `${getDesertScorePresentation(score).label} (${score.toFixed(1)})`;
}

export function sortRegions(regions: RegionSummary[], sortMode: RegionSortMode) {
    return [...regions].sort((a, b) => {
        if (sortMode === 'tier') {
            return (a.cat_tier ?? 99) - (b.cat_tier ?? 99) || a.name.localeCompare(b.name);
        }
        if (sortMode === 'desert') {
            return (b.desert_score ?? -1) - (a.desert_score ?? -1) || a.name.localeCompare(b.name);
        }
        return a.name.localeCompare(b.name);
    });
}

export function filterRegions(
    regions: RegionSummary[],
    query: string,
    filters: SidebarFilters,
) {
    const normalizedQuery = query.trim().toLowerCase();

    return regions.filter(region => {
        if (
            normalizedQuery
            && !region.name.toLowerCase().includes(normalizedQuery)
            && !region.region_code.toLowerCase().includes(normalizedQuery)
        ) {
            return false;
        }

        if (filters.tier && String(region.cat_tier ?? '') !== filters.tier) {
            return false;
        }

        if (
            filters.status
            && (region.telehealth_status || '').toLowerCase() !== filters.status.toLowerCase()
        ) {
            return false;
        }

        if (!matchesDesertScoreFilter(region.desert_score, filters.desert)) {
            return false;
        }

        if (filters.dataGap === 'missing' && !region.has_data_gap) {
            return false;
        }

        if (filters.dataGap === 'complete' && region.has_data_gap) {
            return false;
        }

        return true;
    });
}
