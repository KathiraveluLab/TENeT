/**
 * API client for CAT (Community Access Tier) data
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001/api/cat';

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

/**
 * Fetch all CAT regions
 */
export async function fetchRegions(tier?: number): Promise<CATRegion[]> {
    const url = tier
        ? `${API_BASE}/regions?tier=${tier}`
        : `${API_BASE}/regions`;

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
