/**
 * API client for CAT (Community Access Tier) data
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/cat';

// Season type for user-selected seasonal scenario
export type Season = 'summer' | 'winter' | 'year_round';

// Filter modes for Gap Hunter layer
export type PerformanceFilterType = 'combined' | 'affordability' | 'latency';

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
    necessity_score: number;
}

export interface RegionsResponse {
    regions: CATRegion[];
    total: number;
}

export type TelehealthStatusName =
    | 'TELEHEALTH_READY'
    | 'COMMUNITY_ANCHOR'
    | 'CRITICAL_GAP'
    | 'DATA_UNAVAILABLE';

export type AffordabilityStatusName = 'affordable' | 'unaffordable' | 'unknown';

export interface RegionSummary {
    id: number;
    region_code: string;
    name: string;
    lat: number | null;
    lon: number | null;
    cat_tier: number | null;
    telehealth_status: TelehealthStatusName | string;
    desert_score: number | null;
    affordability_status: AffordabilityStatusName | string;
    data_confidence: 'high' | 'medium' | 'low' | 'missing' | 'unknown' | string;
    has_data_gap: boolean;
    region: string | null;
}

export interface RegionSummaryResponse {
    regions: RegionSummary[];
    count: number;
}

export interface RegionSearchParams {
    q?: string;
    name?: string;
    tier?: number | string | null;
    status?: string | null;
    desert_min?: number | string | null;
    desert_max?: number | string | null;
    data_gap?: boolean | string | null;
    region?: string | null;
}

export interface RegionSearchResponse extends RegionSummaryResponse {
    filters?: Record<string, unknown>;
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
 * Fetch lightweight community summaries for sidebar navigation.
 */
export async function fetchRegionSummary(): Promise<RegionSummary[]> {
    const response = await fetch(`${API_BASE}/regions/summary`);
    if (!response.ok) {
        throw new Error(`Failed to fetch region summary: ${response.statusText}`);
    }

    const data: RegionSummaryResponse = await response.json();
    return data.regions;
}

/**
 * Search lightweight community summaries for sidebar discovery.
 */
export async function searchRegions(params: RegionSearchParams = {}): Promise<RegionSummary[]> {
    const query = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            query.append(key, String(value));
        }
    });

    const suffix = query.toString() ? `?${query.toString()}` : '';
    const response = await fetch(`${API_BASE}/regions/search${suffix}`);
    if (!response.ok) {
        throw new Error(`Failed to search regions: ${response.statusText}`);
    }

    const data: RegionSearchResponse = await response.json();
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
 * Get map color based on Telehealth Necessity Score (0-100)
 */
export function getNeedColor(score: number): string {
    if (score >= 75) return '#ef4444';      // Red - Critical Need
    if (score >= 50) return '#f97316';      // Orange - High Need
    if (score >= 25) return '#eab308';      // Yellow - Moderate Need
    return '#22c55e';                       // Green - Low Need
}

/**
 * Get label based on Telehealth Necessity Score (0-100)
 */
export function getNeedLabel(score: number): string {
    if (score >= 75) return 'Critical Need';
    if (score >= 50) return 'High Need';
    if (score >= 25) return 'Moderate Need';
    return 'Adequate Need';
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
            return { icon: '', label: 'Satellite Only', severity: 'warning' };
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
            return { icon: '', label: gap, severity: 'info' };
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

// =============================================================================
// Ookla Performance Layer API (Measured Network Performance)
// =============================================================================

export interface PerformanceTile {
    quadkey: string;
    lat: number;
    lon: number;
    avg_d_mbps: number | null;
    avg_u_mbps: number | null;
    avg_lat_ms: number | null;
    tests: number;
    devices: number;
    color: string;
    label: string;
}

export interface PerformanceResponse {
    tiles: PerformanceTile[];
    count: number;
    year: number;
    quarter: number;
    summary: {
        avg_download_mbps: number | null;
        avg_latency_ms: number | null;
        total_tests: number;
        total_devices: number;
        tiles_excellent: number;
        tiles_good: number;
        tiles_poor: number;
    };
}

export interface ServiceGap {
    place_id: string;
    place_name: string;
    region_code: string | null;
    lat: number;
    lon: number;
    fcc_claimed_pct: number;
    fcc_advertised_mbps: number;
    ookla_measured_mbps: number;
    reliability_score: number;  // Ookla / FCC ratio (0-1+)
    gap_severity: 'CRITICAL' | 'MAJOR' | 'MINOR';
    gap_color: string;
    sample_size: number;
    gap_explanation: string;
}

export interface ServiceGapsResponse {
    gaps: ServiceGap[];
    count: number;
    critical_gaps: number;
    major_gaps: number;
    description: string;
    methodology: {
        reliability_formula: string;
        critical_threshold: string;
        major_threshold: string;
        minor_threshold: string;
    };
}

export interface RegionPerformance {
    region_code: string;
    region_name: string;
    has_data: boolean;
    performance?: {
        avg_download_mbps: number;
        avg_upload_mbps: number | null;
        avg_latency_ms: number;
        total_tests: number;
        total_devices: number;
        tile_count: number;
        speed_label: string;
        speed_color: string;
    };
    fcc_comparison?: {
        fcc_claimed_coverage_pct: number | null;
        is_service_gap: boolean;
        gap_explanation: string | null;
    };
}

export interface PerformanceSummary {
    has_data: boolean;
    period: {
        year: number;
        quarter: number;
        label: string;
    };
    coverage: {
        total_tiles: number;
        tiles_with_speed_data: number;
        total_tests: number;
        total_devices: number;
    };
    speeds: {
        avg_download_mbps: number | null;
        max_download_mbps: number | null;
        min_download_mbps: number | null;
        median_download_mbps: number | null;
    };
    distribution: {
        excellent: number;
        good: number;
        moderate: number;
        poor: number;
        critical: number;
    };
    telehealth_viable_pct: number;
}

/**
 * Fetch Ookla performance tiles
 */
export async function fetchPerformance(
    year?: number,
    quarter?: number,
    minTests: number = 1
): Promise<PerformanceResponse> {
    let url = `${API_BASE}/performance?min_tests=${minTests}`;
    if (year) url += `&year=${year}`;
    if (quarter) url += `&quarter=${quarter}`;

    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Failed to fetch performance: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Fetch service gaps (FCC claims vs Ookla measured)
 */
export async function fetchServiceGaps(): Promise<ServiceGapsResponse> {
    const response = await fetch(`${API_BASE}/performance/gaps`);
    if (!response.ok) {
        throw new Error(`Failed to fetch service gaps: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Fetch performance for a specific region
 */
export async function fetchRegionPerformance(regionCode: string): Promise<RegionPerformance> {
    const response = await fetch(`${API_BASE}/performance/by-region/${regionCode}`);
    if (!response.ok) {
        throw new Error(`Failed to fetch region performance: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Fetch performance summary
 */
export async function fetchPerformanceSummary(): Promise<PerformanceSummary> {
    const response = await fetch(`${API_BASE}/performance/summary`);
    if (!response.ok) {
        throw new Error(`Failed to fetch performance summary: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Get speed color for visualization
 */
export function getSpeedColor(speedMbps: number | null): string {
    if (speedMbps === null) return '#6b7280';  // Gray - no data
    if (speedMbps >= 50) return '#22c55e';     // Green - excellent
    if (speedMbps >= 25) return '#84cc16';     // Lime - good
    if (speedMbps >= 10) return '#eab308';     // Yellow - moderate
    if (speedMbps >= 5) return '#f97316';      // Orange - poor
    return '#ef4444';                           // Red - critical
}

/**
 * Get speed label
 */
export function getSpeedLabel(speedMbps: number | null): string {
    if (speedMbps === null) return 'No Data';
    if (speedMbps >= 50) return 'Excellent';
    if (speedMbps >= 25) return 'Good';
    if (speedMbps >= 10) return 'Moderate';
    if (speedMbps >= 5) return 'Poor';
    return 'Critical';
}

// ============================================================================
// TOP GAPS (Gap Hunter)
// ============================================================================

export interface TopGap {
    rank: number;
    name: string;
    region: string;
    lat: number;
    lon: number;
    quadkey: string;
    speed_mbps: number;
    tests: number;
    devices: number;
    severity: 'critical' | 'poor' | 'moderate';
    severity_label: string;
    color: string;
    gap_from_threshold: number;
}

export interface TopGapsResponse {
    gaps: TopGap[];
    count: number;
    period: string;
    threshold_mbps: number;
}

/**
 * Fetch top priority gaps with location names
 */
export async function fetchTopGaps(limit: number = 10): Promise<TopGapsResponse> {
    const response = await fetch(`${API_BASE}/performance/top-gaps?limit=${limit}`);
    if (!response.ok) {
        throw new Error(`Failed to fetch top gaps: ${response.statusText}`);
    }
    return response.json();
}

export interface LocationInfo {
    name: string;
    region: string;
    country: string;
    lat: number;
    lon: number;
}

/**
 * Fetch location name for given coordinates (reverse geocoding)
 */
export async function fetchLocationName(lat: number, lon: number): Promise<LocationInfo> {
    const response = await fetch(`${API_BASE}/performance/location?lat=${lat}&lon=${lon}`);
    if (!response.ok) {
        return { name: 'Unknown', region: '', country: '', lat, lon };
    }
    return response.json();
}

// =============================================================================
// AFFORDABILITY ANALYSIS
// =============================================================================

export interface AffordabilityZone {
    zcta: string;
    lat: number | null;
    lon: number | null;
    median_income: number;
    monthly_income: number;
    internet_cost: number;
    isp: string;
    isp_description: string;
    burden_pct: number;
    status: 'AFFORDABLE' | 'UNAFFORDABLE';
    is_affordable: boolean;
    color: string;
    population: number | null;
    households: number | null;
}

export interface AffordabilityResponse {
    zones: AffordabilityZone[];
    count: number;
    monthly_cost: number;
    threshold_pct: number;
    summary: {
        affordable: number;
        unaffordable: number;
        affordable_pct: number;
    };
}

export interface CombinedAccessZone {
    zcta: string;
    lat: number | null;
    lon: number | null;
    avg_speed_mbps: number;
    has_coverage: boolean;
    median_income: number;
    monthly_income: number;
    burden_pct: number;
    is_affordable: boolean;
    status: 'TRUE_ACCESS' | 'COVERAGE_NO_ACCESS' | 'INFRASTRUCTURE_GAP';
    status_label: string;
    color: string;
    population: number | null;
    tests: number;
}

export interface CombinedAccessResponse {
    combined: CombinedAccessZone[];
    count: number;
    monthly_cost: number;
    summary: {
        true_access: number;
        coverage_without_access: number;
        infrastructure_gap: number;
        true_access_pct: number;
    };
}

/**
 * Fetch affordability analysis by ZCTA
 * @param monthlyCost - Internet cost per month (default: $120 for Starlink)
 * @param threshold - Affordability threshold as % of income (default: 2.0)
 */
export async function fetchAffordability(
    monthlyCost: number = 120,
    threshold: number = 2.0
): Promise<AffordabilityResponse> {
    const response = await fetch(
        `${API_BASE}/performance/affordability?monthly_cost=${monthlyCost}&threshold=${threshold}`
    );
    if (!response.ok) {
        throw new Error(`Failed to fetch affordability data: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Fetch combined speed + affordability analysis
 * Shows TRUE_ACCESS, COVERAGE_NO_ACCESS, and INFRASTRUCTURE_GAP zones
 * @param monthlyCost - Internet cost per month (default: $120)
 */
export async function fetchCombinedAccess(monthlyCost: number = 120): Promise<CombinedAccessResponse> {
    const response = await fetch(
        `${API_BASE}/performance/affordability/combined?monthly_cost=${monthlyCost}`
    );
    if (!response.ok) {
        throw new Error(`Failed to fetch combined access data: ${response.statusText}`);
    }
    return response.json();
}

// =============================================================================
// REGION AFFORDABILITY & SAFETY NET
// =============================================================================

export interface RegionAffordability {
    has_income_data: boolean;
    income_source: 'ZCTA' | 'Borough' | 'unavailable';
    zcta?: string;
    distance_km?: number;
    median_income?: number;
    monthly_income?: number;
    internet_cost?: number;
    isp?: string;
    burden_pct?: number;
    threshold_pct?: number;
    is_affordable?: boolean;
    status?: 'AFFORDABLE' | 'UNAFFORDABLE';
    message?: string;
    region_code: string;
    region_name: string;
}

export interface SafetyNetClassification {
    region_code: string;
    region_name: string;
    has_nearby_clinic: boolean;
    distance_threshold_km: number;
    access_mode: string;
    nearest_clinic: {
        name: string | null;
        type: string | null;
        distance_km: number | null;
    } | null;
    classification: 'COMMUNITY_SUPPORTED' | 'CRITICAL' | 'AT_RISK';
    classification_color: string;
    description: string;
}

/**
 * Fetch affordability analysis for a specific region
 */
export async function fetchRegionAffordability(regionCode: string): Promise<RegionAffordability> {
    const response = await fetch(`${API_BASE}/regions/${regionCode}/affordability`);
    if (!response.ok) {
        throw new Error(`Failed to fetch region affordability: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Fetch safety net classification for a specific region
 */
export async function fetchRegionSafetyNet(regionCode: string): Promise<SafetyNetClassification> {
    const response = await fetch(`${API_BASE}/regions/${regionCode}/safety-net`);
    if (!response.ok) {
        throw new Error(`Failed to fetch safety net classification: ${response.statusText}`);
    }
    return response.json();
}

// =============================================================================
// COMPOSITE TELEHEALTH STATUS
// =============================================================================

export interface TelehealthStatus {
    region_code: string;
    region_name: string;
    status: 'TELEHEALTH_READY' | 'COMMUNITY_ANCHOR' | 'CRITICAL_GAP' | 'DATA_UNAVAILABLE';
    color: string;
    label: string;
    description: string;
    affordability: {
        has_data: boolean;
        is_affordable: boolean;
        burden_pct: number | null;
        internet_cost: number | null;
    };
    clinic_proximity: {
        has_nearby: boolean;
        nearest_name: string | null;
        nearest_distance_km: number | null;
        threshold_km: number;
    };
}

/**
 * Fetch composite telehealth status for a region
 * Combines affordability + clinic proximity into a single classification
 */
export async function fetchTelehealthStatus(regionCode: string): Promise<TelehealthStatus> {
    const response = await fetch(`${API_BASE}/regions/${regionCode}/telehealth-status`);
    if (!response.ok) {
        throw new Error(`Failed to fetch telehealth status: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Get the color to use for a region marker based on telehealth status
 */
export function getTelehealthStatusColor(status: TelehealthStatus['status']): string {
    switch (status) {
        case 'TELEHEALTH_READY':
            return '#22c55e';  // Green
        case 'COMMUNITY_ANCHOR':
            return '#f59e0b';  // Amber
        case 'CRITICAL_GAP':
            return '#ef4444';  // Red
        case 'DATA_UNAVAILABLE':
        default:
            return '#6b7280';  // Gray
    }
}

// Bulk telehealth status for all regions
export interface RegionTelehealthStatus {
    region_code: string;
    region_name: string;
    lat: number;
    lon: number;
    status: 'TELEHEALTH_READY' | 'COMMUNITY_ANCHOR' | 'CRITICAL_GAP' | 'DATA_UNAVAILABLE';
    color: string;
    internet_cost: number | null;
    isp_name: string;
    burden_pct: number | null;
    median_income: number | null;
    has_nearby_clinic: boolean;
    nearest_clinic_name: string | null;
    nearest_clinic_km: number | null;
    access_mode: string;
    recommendation: string;
}

export interface AllTelehealthStatusResponse {
    regions: RegionTelehealthStatus[];
    count: number;
    summary: {
        telehealth_ready: number;
        community_anchor: number;
        critical_gap: number;
        data_unavailable: number;
    };
}

/**
 * Fetch telehealth status for ALL regions (used by Affordability Layer)
 */
export async function fetchAllTelehealthStatus(): Promise<AllTelehealthStatusResponse> {
    const response = await fetch(`${API_BASE}/telehealth-status/all`);
    if (!response.ok) {
        throw new Error(`Failed to fetch all telehealth status: ${response.statusText}`);
    }
    return response.json();
}
