import type { StatusTone } from '../components/ui/StatusBadge';
import type { TelehealthStatusName } from './statusPresentation';

export type CatTier = 1 | 2 | 3 | 4;

interface CatTierPresentation {
    label: string;
    shortDescription: string;
    color: string;
    tone: StatusTone;
}

export const CAT_TIER_PRESENTATION: Record<CatTier, CatTierPresentation> = {
    1: {
        label: 'Full Multimodal Access',
        shortDescription: 'strongest access; road-connected or easier service reach.',
        color: '#22c55e',
        tone: 'ready',
    },
    2: {
        label: 'Dual Mode Access',
        shortDescription: 'moderate access; some travel or logistics constraints.',
        color: '#eab308',
        tone: 'info',
    },
    3: {
        label: 'Limited Access',
        shortDescription: 'limited access; remote travel makes care harder to reach.',
        color: '#f97316',
        tone: 'anchor',
    },
    4: {
        label: 'Extreme/No Direct Access',
        shortDescription: 'most isolated; highest transport and service-access barriers.',
        color: '#ef4444',
        tone: 'critical',
    },
};

export const CAT_TIERS = [1, 2, 3, 4] as const;

export interface DesertScorePresentation {
    level: 'adequate' | 'moderate' | 'high' | 'critical';
    label: string;
    color: string;
    tone: StatusTone;
    description: string;
}

export const DESERT_SCORE_THRESHOLDS = {
    moderate: 25,
    high: 50,
    critical: 75,
} as const;

const REGION_CARD_SEVERITY_THRESHOLDS = {
    warning: 60,
    critical: 80,
} as const;

export function getDesertScorePresentation(score: number): DesertScorePresentation {
    if (score >= DESERT_SCORE_THRESHOLDS.critical) {
        return {
            level: 'critical',
            label: 'Critical Need',
            color: '#f43f5e',
            tone: 'critical',
            description: 'Severe lack of nearby healthcare facilities',
        };
    }
    if (score >= DESERT_SCORE_THRESHOLDS.high) {
        return {
            level: 'high',
            label: 'High Need',
            color: '#fb923c',
            tone: 'anchor',
            description: 'Limited access to clinics or hospitals',
        };
    }
    if (score >= DESERT_SCORE_THRESHOLDS.moderate) {
        return {
            level: 'moderate',
            label: 'Moderate Need',
            color: '#fbbf24',
            tone: 'info',
            description: 'Adequate access with some travel distance',
        };
    }
    return {
        level: 'adequate',
        label: 'Adequate Need',
        color: '#34d399',
        tone: 'ready',
        description: 'Good access to nearby healthcare facilities',
    };
}

export type DesertScoreFilter = '' | '75-plus' | '50-plus' | 'below-50' | 'unknown';

export const DESERT_SCORE_FILTER_OPTIONS: Array<{ value: DesertScoreFilter; label: string }> = [
    { value: '', label: 'All scores' },
    { value: '75-plus', label: `${DESERT_SCORE_THRESHOLDS.critical}+ critical need` },
    { value: '50-plus', label: `${DESERT_SCORE_THRESHOLDS.high}+ high need` },
    { value: 'below-50', label: `Below ${DESERT_SCORE_THRESHOLDS.high}` },
    { value: 'unknown', label: 'Unknown score' },
];

export function matchesDesertScoreFilter(
    score: number | null | undefined,
    filter: DesertScoreFilter,
): boolean {
    if (!filter) return true;
    if (filter === 'unknown') return score === null || score === undefined;
    if (score === null || score === undefined) return false;
    if (filter === '75-plus') return score >= DESERT_SCORE_THRESHOLDS.critical;
    if (filter === '50-plus') return score >= DESERT_SCORE_THRESHOLDS.high;
    return score < DESERT_SCORE_THRESHOLDS.high;
}

export function getRegionSeverityClassName(region: {
    telehealth_status: TelehealthStatusName;
    desert_score: number | null;
}): string {
    const status: TelehealthStatusName = region.telehealth_status;
    const score = region.desert_score ?? -1;
    // These existing card-emphasis cutoffs are intentionally distinct from the
    // canonical 25/50/75 desert-score meaning bands above.
    if (status === 'CRITICAL_GAP' || score >= REGION_CARD_SEVERITY_THRESHOLDS.critical) return 'severity-critical';
    if (status === 'COMMUNITY_ANCHOR' || score >= REGION_CARD_SEVERITY_THRESHOLDS.warning) return 'severity-warning';
    if (status === 'TELEHEALTH_READY') return 'severity-ready';
    return 'severity-unknown';
}

export type DataGapSeverity = 'warning' | 'error' | 'info';

export type DataConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export const DATA_CONFIDENCE_PRESENTATION: Record<DataConfidenceLevel, {
    label: string;
    className: string;
}> = {
    HIGH: { label: 'High', className: 'is-high' },
    MEDIUM: { label: 'Medium', className: 'is-medium' },
    LOW: { label: 'Low', className: 'is-low' },
};

export const DATA_CONFIDENCE_LEVELS: DataConfidenceLevel[] = ['HIGH', 'MEDIUM', 'LOW'];

export function getDataGapPresentation(gap: string): { label: string; severity: DataGapSeverity } {
    switch (gap) {
        case 'SATELLITE_DEPENDENT':
            return { label: 'Satellite-dependent access', severity: 'warning' };
        case 'LOW_TERRESTRIAL':
            return { label: 'Low wired coverage', severity: 'warning' };
        case 'LOW_CONFIDENCE':
            return { label: 'Low data confidence', severity: 'info' };
        case 'INTERNET_DESERT':
            return { label: 'No internet coverage', severity: 'error' };
        case 'MISSING_WIRED_DATA':
            return { label: 'Missing wired data', severity: 'info' };
        case 'MISSING_SATELLITE_DATA':
            return { label: 'Missing satellite data', severity: 'info' };
        default:
            return { label: gap, severity: 'info' };
    }
}

export const SATELLITE_PRIMARY_METRIC = {
    label: 'Satellite-primary places',
    description: 'This is a connectivity access type, not a measure of affordability.',
} as const;
