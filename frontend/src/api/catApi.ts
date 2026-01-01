/**
 * API client for CAT (Community Access Tier) data
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001/api/cat';

// Season type for user-selected seasonal scenario
export type Season = 'summer' | 'winter' | 'year_round';

export interface CATRegion {
    region_code: string;
    region_name: string;
    tier_level: number;
    description: string;
    centroid_lat: number | null;
    centroid_lon: number | null;
    population: number | null;
    area_sqkm: number | null;
    access_score: number | null;
}

export interface RegionsResponse {
    regions: CATRegion[];
    total: number;
}

export interface StatisticsResponse {
    total_regions: number;
    total_data_points: number;
    total_uploads: number;
    completed_uploads: number;
    total_gating_rules: number;
    active_gating_rules: number;
    total_healthcare_sites: number;
    hospitals: number;
    clinics: number;
}

export interface SeasonScenario {
    active_season: Season;
    season_display: string;
    road_quality: string;
    assumption: string;
}

export interface TelehealthPriorityResponse {
    region_code: string;
    region_name: string;
    cat_tier: number;
    necessity_score: number;
    connectivity_score: number;
    combined_priority: number;
    priority: 'HIGH' | 'CRITICAL' | 'MODERATE' | 'LOW';
    color: string;
    label: string;
    recommendation: string;
    season_scenario: SeasonScenario;
    healthcare_details: {
        necessity_score: number;
        distance_to_nearest_clinic_km: number;
        num_healthcare_sites: number;
        has_specialist_access: boolean;
        breakdown: {
            distance_component: number;
            density_component: number;
            specialist_component: number;
            transport_component: number;
            transport_season_adjusted: boolean;
        };
    };
    connectivity_details: {
        bandwidth_mbps: number | null;
        latency_ms: number | null;
        feasible_for_video: boolean;
    };
}

/**
 * Fetch all CAT regions with optional season adjustment
 */
export async function fetchRegions(season: Season = 'year_round', tier?: number): Promise<CATRegion[]> {
    let url = `${API_BASE}/regions?season=${season}`;
    if (tier) {
        url += `&tier=${tier}`;
    }

    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Failed to fetch regions: ${response.statusText}`);
    }

    const data: RegionsResponse = await response.json();
    return data.regions;
}

/**
 * Fetch database statistics
 */
export async function fetchStatistics(): Promise<StatisticsResponse> {
    const response = await fetch(`${API_BASE}/statistics`);
    if (!response.ok) {
        throw new Error(`Failed to fetch statistics: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Fetch telehealth priority for a region with season adjustment
 */
export async function fetchTelehealthPriority(
    regionCode: string,
    season: Season = 'year_round'
): Promise<TelehealthPriorityResponse> {
    const url = `${API_BASE}/telehealth-priority/${regionCode}?season=${season}`;

    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Failed to fetch telehealth priority: ${response.statusText}`);
    }

    return response.json();
}

/**
 * Get tier color based on CAT tier level
 */
export function getTierColor(tier: number): string {
    switch (tier) {
        case 1: return '#22c55e'; // Green - Full access
        case 2: return '#eab308'; // Yellow - Dual mode
        case 3: return '#f97316'; // Orange - Limited
        case 4: return '#ef4444'; // Red - Extreme
        default: return '#6b7280'; // Gray - Unknown
    }
}

/**
 * Get tier label based on CAT tier level
 */
export function getTierLabel(tier: number): string {
    switch (tier) {
        case 1: return 'Full Multimodal Access';
        case 2: return 'Dual Mode Access';
        case 3: return 'Limited Access';
        case 4: return 'Extreme/No Direct Access';
        default: return 'Unknown';
    }
}

/**
 * Get priority color for telehealth classification
 */
export function getPriorityColor(priority: string): string {
    switch (priority) {
        case 'HIGH': return '#22c55e';      // Green
        case 'CRITICAL': return '#ef4444';   // Red
        case 'MODERATE': return '#f97316';   // Orange
        case 'LOW': return '#3b82f6';        // Blue
        default: return '#6b7280';           // Gray
    }
}

