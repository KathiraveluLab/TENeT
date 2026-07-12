/**
 * Scenario Analysis types
 */
import { Season } from '../api/catApi';
import type { ScenarioTelehealthStatusName } from '../domain/statusPresentation';

/** Scenario lifecycle states */
export type ScenarioMode = 'off' | 'calculating' | 'active';

/** User-adjustable thresholds */
export interface ScenarioThresholds {
    min_download_mbps: number;
    min_upload_mbps: number;
    max_latency_ms: number | null;
    clinic_proximity_km: number | null;
    affordability_burden_pct: number;
}

/** Status delta direction */
export type StatusDelta = 'improved' | 'worsened' | 'unchanged';

/** Per-region scenario result */
export interface ScenarioRegion {
    region_code: string;
    name: string;
    lat: number | null;
    lon: number | null;
    baseline_status: ScenarioTelehealthStatusName;
    scenario_status: ScenarioTelehealthStatusName;
    status_delta: StatusDelta;
    baseline_need_score: number;
    scenario_need_score: number;
    need_score_delta: number;
    changed: boolean;
    has_data_gap: boolean;
    missing_fields: string[];
    data_confidence: string;
    reason_codes: string[];
    explanation: string;
}

/** Summary statistics */
export interface ScenarioSummary {
    total_regions: number;
    status_changed_regions: number;
    score_changed_regions: number;
    improved_count: number;
    worsened_count: number;
    unchanged_count: number;
    telehealth_ready: number;
    community_anchor: number;
    limited_telehealth: number;
    critical_gap: number;
    data_unavailable: number;
}

/** Full preview response */
export interface ScenarioPreviewResponse {
    scenario: {
        season: Season;
        thresholds: ScenarioThresholds;
        is_baseline_equivalent: boolean;
    };
    summary: ScenarioSummary;
    regions: ScenarioRegion[];
}

/** Preset definitions */
export interface ScenarioPreset {
    id: string;
    label: string;
    thresholds: Partial<ScenarioThresholds>;
}

/** Preset options */
export const SCENARIO_PRESETS: ScenarioPreset[] = [
    {
        id: 'fcc',
        label: 'Baseline (25/3 Mbps)',
        thresholds: {
            min_download_mbps: 25,
            min_upload_mbps: 3,
            affordability_burden_pct: 2,
        },
    },
    {
        id: 'equity',
        label: 'Broadband Equity Goal',
        thresholds: {
            min_download_mbps: 100,
            min_upload_mbps: 20,
        },
    },
    {
        id: 'clinic_access',
        label: 'Universal Clinic Access',
        thresholds: {
            clinic_proximity_km: 25,
        },
    },
];

/** Default baseline thresholds */
export const BASELINE_THRESHOLDS: ScenarioThresholds = {
    min_download_mbps: 25,
    min_upload_mbps: 3,
    max_latency_ms: 150,
    clinic_proximity_km: null,
    affordability_burden_pct: 2,
};

export function getScenarioDeltaColor(delta: StatusDelta): string {
    switch (delta) {
        case 'improved': return '#22c55e';
        case 'worsened': return '#ef4444';
        case 'unchanged': return '#94a3b8';
    }
}

export function getScenarioStatusColor(status: ScenarioTelehealthStatusName | string): string {
    switch (status) {
        case 'TELEHEALTH_READY': return '#22c55e';
        case 'COMMUNITY_ANCHOR': return '#f97316';
        case 'LIMITED_TELEHEALTH': return '#eab308';
        case 'CRITICAL_GAP': return '#ef4444';
        case 'DATA_UNAVAILABLE': return '#6b7280';
        default: return '#94a3b8';
    }
}
