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

// =============================================================================
// Broadband Coverage & Data Gaps API (Data Coverage Layer)
// =============================================================================

export interface BroadbandCoverage {
    place_id: string;
    place_name: string;
    residential_units: number | null;
    coverage: {
        any_tech_25mbps_pct: number | null;
        any_tech_100mbps_pct: number | null;
        wired_25mbps_pct: number | null;
        ngso_satellite_25mbps_pct: number | null;
        fiber_25mbps_pct: number | null;
    };
    confidence: 'HIGH' | 'MEDIUM' | 'LOW';
    data_gaps: string[];
    telehealth_viable: 'YES' | 'NO' | 'UNCERTAIN';
    primary_access: 'WIRED' | 'SATELLITE' | 'LIMITED';
    region_code: string | null;
    data_source: string;
}

export interface DataGapsSummary {
    total_places: number;
    places_with_gaps: number;
    gap_breakdown: {
        [key: string]: {
            count: number;
            percentage: number;
            places: { place_id: string; place_name: string; confidence: string }[];
        };
    };
    confidence_distribution: {
        HIGH: number;
        MEDIUM: number;
        LOW: number;
    };
    telehealth_viability: {
        YES: number;
        NO: number;
        UNCERTAIN: number;
    };
    primary_access: {
        WIRED: number;
        SATELLITE: number;
        LIMITED: number;
    };
}

export interface BroadbandResponse {
    broadband: BroadbandCoverage[];
    count: number;
    summary: {
        by_confidence: { HIGH: number; MEDIUM: number; LOW: number };
        satellite_dependent: number;
        with_data_gaps: number;
        low_confidence: number;
    };
}

/**
 * Fetch broadband coverage data
 */
export async function fetchBroadbandCoverage(filters?: {
    confidence?: string;
    telehealth_viable?: string;
    primary_access?: string;
    has_gaps?: boolean;
}): Promise<BroadbandResponse> {
    let url = `${API_BASE}/broadband`;
    const params = new URLSearchParams();

    if (filters?.confidence) params.append('confidence', filters.confidence);
    if (filters?.telehealth_viable) params.append('telehealth_viable', filters.telehealth_viable);
    if (filters?.primary_access) params.append('primary_access', filters.primary_access);
    if (filters?.has_gaps) params.append('has_gaps', 'true');

    if (params.toString()) {
        url += `?${params.toString()}`;
    }

    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Failed to fetch broadband data: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Fetch data gaps summary for dashboard display
 */
export async function fetchDataGapsSummary(): Promise<DataGapsSummary> {
    const response = await fetch(`${API_BASE}/data-gaps`);
    if (!response.ok) {
        throw new Error(`Failed to fetch data gaps: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Get confidence color for data quality visualization
 */
export function getConfidenceColor(confidence: string): string {
    switch (confidence) {
        case 'HIGH': return '#22c55e';    // Green
        case 'MEDIUM': return '#eab308';   // Yellow
        case 'LOW': return '#ef4444';      // Red
        default: return '#6b7280';         // Gray
    }
}

/**
 * Get icon/label for data gap types
 */
export function getDataGapInfo(gap: string): { icon: string; label: string; severity: 'warning' | 'error' | 'info' } {
    switch (gap) {
        case 'SATELLITE_DEPENDENT':
            return { icon: '📡', label: 'Satellite Only', severity: 'warning' };
        case 'LOW_TERRESTRIAL':
            return { icon: '📶', label: 'Low Wired Coverage', severity: 'warning' };
        case 'LOW_CONFIDENCE':
            return { icon: '❓', label: 'Low Data Confidence', severity: 'info' };
        case 'INTERNET_DESERT':
            return { icon: '🚫', label: 'No Internet Coverage', severity: 'error' };
        case 'MISSING_WIRED_DATA':
            return { icon: '📊', label: 'Missing Wired Data', severity: 'info' };
        case 'MISSING_SATELLITE_DATA':
            return { icon: '📊', label: 'Missing Satellite Data', severity: 'info' };
        default:
            return { icon: '⚠️', label: gap, severity: 'info' };
    }
}

// =============================================================================
// Healthcare Facility API
// =============================================================================

export interface HealthcareFacility {
    id: number;
    name: string;
    type: 'hospital' | 'clinic' | 'pharmacy' | 'health_center';
    distance_km?: number;
    latitude: number;
    longitude: number;
    has_emergency: boolean;
    has_specialists: boolean;
    has_telehealth: boolean;
    phone?: string;
    website?: string;
    address?: string;
    beds?: number;
}

export interface HealthcareByRegion {
    region_code: string;
    region_name: string;
    facilities: HealthcareFacility[];
    count: number;
    nearest_hospital: {
        name: string;
        distance_km: number;
    } | null;
    nearest_clinic: {
        name: string;
        distance_km: number;
    } | null;
}

export interface HealthcareSummary {
    total_facilities: number;
    by_type: {
        hospital: number;
        clinic: number;
        pharmacy: number;
        health_center: number;
    };
    features: {
        with_emergency: number;
        with_specialists: number;
        with_telehealth: number;
    };
    data_source: string;
}

/**
 * Fetch healthcare facilities near a specific region
 */
export async function fetchHealthcareByRegion(regionCode: string, limit = 10): Promise<HealthcareByRegion> {
    const response = await fetch(`${API_BASE}/healthcare/by-region/${regionCode}?limit=${limit}`);
    if (!response.ok) {
        throw new Error(`Failed to fetch healthcare data: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Fetch healthcare summary statistics
 */
export async function fetchHealthcareSummary(): Promise<HealthcareSummary> {
    const response = await fetch(`${API_BASE}/healthcare/summary`);
    if (!response.ok) {
        throw new Error(`Failed to fetch healthcare summary: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Get facility type icon and color
 */
export function getFacilityTypeInfo(type: string): { icon: string; color: string; label: string } {
    switch (type) {
        case 'hospital':
            return { icon: '🏥', color: '#dc2626', label: 'Hospital' };
        case 'clinic':
            return { icon: '🩺', color: '#2563eb', label: 'Clinic' };
        case 'pharmacy':
            return { icon: '💊', color: '#16a34a', label: 'Pharmacy' };
        case 'health_center':
            return { icon: '🏨', color: '#7c3aed', label: 'Health Center' };
        default:
            return { icon: '🏥', color: '#6b7280', label: type };
    }
}

