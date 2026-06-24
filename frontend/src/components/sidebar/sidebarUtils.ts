import { RegionSummary } from '../../api/catApi';

export type RegionSortMode = 'name' | 'tier' | 'desert';
export type DataGapFilter = 'all' | 'missing' | 'complete';

export interface SidebarFilters {
    tier: string;
    status: string;
    desert: string;
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

export function statusClassName(status: string | null | undefined) {
    const normalized = (status || '').toLowerCase();
    if (normalized.includes('ready')) return 'status-ready';
    if (normalized.includes('anchor')) return 'status-anchor';
    if (normalized.includes('critical')) return 'status-critical';
    return 'status-unknown';
}

export function telehealthNeedLabel(score: number | null | undefined): string {
    if (score === null || score === undefined || !Number.isFinite(score)) {
        return 'Data unavailable';
    }
    if (score <= 30) return `Low Need (${score.toFixed(1)})`;
    if (score <= 60) return `Moderate Need (${score.toFixed(1)})`;
    if (score <= 80) return `High Need (${score.toFixed(1)})`;
    return `Critical Need (${score.toFixed(1)})`;
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

        if (filters.desert === '70-plus' && (region.desert_score ?? -1) < 70) {
            return false;
        }

        if (filters.desert === '50-plus' && (region.desert_score ?? -1) < 50) {
            return false;
        }

        if (filters.desert === 'below-50' && (region.desert_score === null || region.desert_score === undefined || region.desert_score >= 50)) {
            return false;
        }

        if (filters.desert === 'unknown' && region.desert_score !== null && region.desert_score !== undefined) {
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
