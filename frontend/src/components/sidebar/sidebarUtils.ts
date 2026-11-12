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

const STATUS_ALIASES: Record<string, string> = {
    ready: 'telehealth_ready',
    telehealth_ready: 'telehealth_ready',
    telehealthready: 'telehealth_ready',
    anchor: 'community_anchor',
    community_anchor: 'community_anchor',
    communityanchor: 'community_anchor',
    limited: 'limited_telehealth',
    limited_telehealth: 'limited_telehealth',
    limitedtelehealth: 'limited_telehealth',
    critical: 'critical_gap',
    critical_gap: 'critical_gap',
    criticalgap: 'critical_gap',
    unavailable: 'data_unavailable',
    data_unavailable: 'data_unavailable',
    dataunavailable: 'data_unavailable',
    missing: 'data_unavailable',
};

function matchesNumericDesertExpr(score: number | null, expr: string): boolean {
    const match = expr.match(/^(>=|<=|>|<)?\s*(-?\d+(?:\.\d+)?)$/);
    if (!match) {
        return matchesDesertScoreFilter(score, expr as DesertScoreFilter);
    }
    if (score === null || score === undefined || !Number.isFinite(score)) {
        return false;
    }
    const op = match[1] || '>=';
    const threshold = Number(match[2]);
    if (op === '>=') return score >= threshold;
    if (op === '<=') return score <= threshold;
    if (op === '>') return score > threshold;
    return score < threshold;
}

function matchesSearchToken(region: RegionSummary, rawToken: string): boolean {
    const token = rawToken.trim().toLowerCase();
    if (!token) return true;

    const colonIndex = token.indexOf(':');
    if (colonIndex > 0) {
        const key = token.slice(0, colonIndex);
        const value = token.slice(colonIndex + 1).trim();
        if (!value) return true;

        if (key === 'tier') {
            const tiers = value.split(',').map(item => item.trim()).filter(Boolean);
            return tiers.includes(String(region.cat_tier ?? ''));
        }
        if (key === 'status') {
            const target = STATUS_ALIASES[value] || value;
            return (region.telehealth_status || '').toLowerCase() === target;
        }
        if (key === 'desert') {
            return matchesNumericDesertExpr(region.desert_score, value);
        }
        if (key === 'data') {
            if (value === 'missing' || value === 'gap' || value === 'true') {
                return Boolean(region.has_data_gap);
            }
            if (value === 'complete' || value === 'ok' || value === 'false') {
                return !region.has_data_gap;
            }
        }
        if (key === 'region') {
            return (region.region || '').toLowerCase().includes(value);
        }
    }

    return (
        region.name.toLowerCase().includes(token)
        || region.region_code.toLowerCase().includes(token)
        || (region.region || '').toLowerCase().includes(token)
    );
}

export function filterRegions(
    regions: RegionSummary[],
    query: string,
    filters: SidebarFilters,
) {
    const tokens = query.trim().split(/\s+/).filter(Boolean);

    return regions.filter(region => {
        if (tokens.some(token => !matchesSearchToken(region, token))) {
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
