/**
 * API client for CAT (Community Access Tier) data
 */

import { CAT_TIER_PRESENTATION, getDesertScorePresentation, type CatTier } from '../domain/metrics';
import type { TelehealthStatusName } from '../domain/statusPresentation';
import type { Feature, FeatureCollection, MultiPolygon } from 'geojson';
import { ApiError, fetchJson, withQuery } from './http';

export type { TelehealthStatusName } from '../domain/statusPresentation';

export const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/cat';

// Season type for user-selected seasonal scenario
export type Season = 'summer' | 'winter' | 'year_round';

// Filter modes for Gap Hunter layer
export type PerformanceFilterType = 'combined' | 'affordability' | 'latency';

export interface CATRegion {
    region_code: string;
    region_name: string;
    tier_level: CatTier;
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

export interface BoundaryProperties {
    CommunityName: string;
    EconomicRegion: string;
    FIPS: string;
    Census_Area: 'Y' | null;
}

export type BoundaryFeature = Feature<MultiPolygon, BoundaryProperties>;
export type BoundaryCollection = FeatureCollection<MultiPolygon, BoundaryProperties>;

export type AffordabilityStatusName = 'affordable' | 'unaffordable' | 'unknown';
export type RegionDataConfidence = 'high' | 'medium' | 'low' | 'missing' | 'unknown';

export interface RegionSummary {
    id: number;
    region_code: string;
    name: string;
    lat: number | null;
    lon: number | null;
    cat_tier: CatTier | null;
    telehealth_status: TelehealthStatusName;
    desert_score: number | null;
    affordability_status: AffordabilityStatusName;
    data_confidence: RegionDataConfidence;
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
    tier?: CatTier | `${CatTier}` | null;
    status?: TelehealthStatusName | null;
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
    cat_tier: CatTier;
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
export async function fetchRegions(
    season: Season = 'year_round',
    tier?: number,
    signal?: AbortSignal,
): Promise<CATRegion[]> {
    const data = await fetchJson<RegionsResponse>(
        withQuery(`${API_BASE}/regions`, { season, tier: tier || undefined }),
        { signal },
        'Failed to fetch regions',
    );
    return data.regions;
}

export function fetchBoundaries(signal?: AbortSignal): Promise<BoundaryCollection> {
    return fetchJson(`${API_BASE}/boundaries`, { signal }, 'Failed to load boundaries');
}

/**
 * Fetch lightweight community summaries for sidebar navigation.
 */
export async function fetchRegionSummary(signal?: AbortSignal): Promise<RegionSummary[]> {
    const data = await fetchJson<RegionSummaryResponse>(
        `${API_BASE}/regions/summary`,
        { signal },
        'Failed to fetch region summary',
    );
    return data.regions;
}

/**
 * Search lightweight community summaries for sidebar discovery.
 */
export async function searchRegions(
    params: RegionSearchParams = {},
    signal?: AbortSignal,
): Promise<RegionSummary[]> {
    const data = await fetchJson<RegionSearchResponse>(
        withQuery(`${API_BASE}/regions/search`, params),
        { signal },
        'Failed to search regions',
    );
    return data.regions;
}

/**
 * Fetch database statistics
 */
export function fetchStatistics(signal?: AbortSignal): Promise<StatisticsResponse> {
    return fetchJson(`${API_BASE}/statistics`, { signal }, 'Failed to fetch statistics');
}

/**
 * Fetch telehealth priority for a region with season adjustment
 */
export async function fetchTelehealthPriority(
    regionCode: string,
    season: Season = 'year_round',
    signal?: AbortSignal,
): Promise<TelehealthPriorityResponse> {
    return fetchJson(
        withQuery(`${API_BASE}/telehealth-priority/${encodeURIComponent(regionCode)}`, { season }),
        { signal },
        'Failed to fetch telehealth priority',
    );
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
}, signal?: AbortSignal): Promise<BroadbandResponse> {
    return fetchJson(
        withQuery(`${API_BASE}/broadband`, {
            confidence: filters?.confidence,
            telehealth_viable: filters?.telehealth_viable,
            primary_access: filters?.primary_access,
            has_gaps: filters?.has_gaps ? true : undefined,
        }),
        { signal },
        'Failed to fetch broadband data',
    );
}

/**
 * Fetch data gaps summary for dashboard display
 */
export function fetchDataGapsSummary(signal?: AbortSignal): Promise<DataGapsSummary> {
    return fetchJson(`${API_BASE}/data-gaps`, { signal }, 'Failed to fetch data gaps');
}

export function getNeedColor(score: number | null | undefined): string {
    return getDesertScorePresentation(score ?? 0).color;
}

export function getNeedLabel(score: number | null | undefined): string {
    if (score === null || score === undefined) return 'Unknown Need';
    return getDesertScorePresentation(score).label;
}

export function getTierColor(tier: CatTier | number | null | undefined): string {
    if (tier === 1 || tier === 2 || tier === 3 || tier === 4) {
        return CAT_TIER_PRESENTATION[tier].color;
    }
    return '#94a3b8';
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
export function fetchHealthcareByRegion(
    regionCode: string,
    limit = 10,
    signal?: AbortSignal,
): Promise<HealthcareByRegion> {
    return fetchJson(
        withQuery(`${API_BASE}/healthcare/by-region/${encodeURIComponent(regionCode)}`, { limit }),
        { signal },
        'Failed to fetch healthcare data',
    );
}

/**
 * Fetch healthcare summary statistics
 */
export function fetchHealthcareSummary(signal?: AbortSignal): Promise<HealthcareSummary> {
    return fetchJson(`${API_BASE}/healthcare/summary`, { signal }, 'Failed to fetch healthcare summary');
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
    minTests: number = 1,
    signal?: AbortSignal,
): Promise<PerformanceResponse> {
    return fetchJson(
        withQuery(`${API_BASE}/performance`, {
            min_tests: minTests,
            year: year || undefined,
            quarter: quarter || undefined,
        }),
        { signal },
        'Failed to fetch performance',
    );
}

/**
 * Fetch service gaps (FCC claims vs Ookla measured)
 */
export function fetchServiceGaps(signal?: AbortSignal): Promise<ServiceGapsResponse> {
    return fetchJson(`${API_BASE}/performance/gaps`, { signal }, 'Failed to fetch service gaps');
}

/**
 * Fetch performance for a specific region
 */
export function fetchRegionPerformance(
    regionCode: string,
    signal?: AbortSignal,
): Promise<RegionPerformance> {
    return fetchJson(
        `${API_BASE}/performance/by-region/${encodeURIComponent(regionCode)}`,
        { signal },
        'Failed to fetch region performance',
    );
}

/**
 * Fetch performance summary
 */
export function fetchPerformanceSummary(signal?: AbortSignal): Promise<PerformanceSummary> {
    return fetchJson(`${API_BASE}/performance/summary`, { signal }, 'Failed to fetch performance summary');
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
export function fetchTopGaps(limit: number = 10, signal?: AbortSignal): Promise<TopGapsResponse> {
    return fetchJson(
        withQuery(`${API_BASE}/performance/top-gaps`, { limit }),
        { signal },
        'Failed to fetch top gaps',
    );
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
export async function fetchLocationName(
    lat: number,
    lon: number,
    signal?: AbortSignal,
): Promise<LocationInfo> {
    try {
        return await fetchJson(
            withQuery(`${API_BASE}/performance/location`, { lat, lon }),
            { signal },
            'Failed to fetch location name',
        );
    } catch (error: unknown) {
        if (error instanceof ApiError && error.status > 0) {
            return { name: 'Unknown', region: '', country: '', lat, lon };
        }
        throw error;
    }
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
    threshold: number = 2.0,
    signal?: AbortSignal,
): Promise<AffordabilityResponse> {
    return fetchJson(
        withQuery(`${API_BASE}/performance/affordability`, {
            monthly_cost: monthlyCost,
            threshold,
        }),
        { signal },
        'Failed to fetch affordability data',
    );
}

/**
 * Fetch combined speed + affordability analysis
 * Shows TRUE_ACCESS, COVERAGE_NO_ACCESS, and INFRASTRUCTURE_GAP zones
 * @param monthlyCost - Internet cost per month (default: $120)
 */
export function fetchCombinedAccess(
    monthlyCost: number = 120,
    signal?: AbortSignal,
): Promise<CombinedAccessResponse> {
    return fetchJson(
        withQuery(`${API_BASE}/performance/affordability/combined`, { monthly_cost: monthlyCost }),
        { signal },
        'Failed to fetch combined access data',
    );
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
export function fetchRegionAffordability(
    regionCode: string,
    signal?: AbortSignal,
): Promise<RegionAffordability> {
    return fetchJson(
        `${API_BASE}/regions/${encodeURIComponent(regionCode)}/affordability`,
        { signal },
        'Failed to fetch region affordability',
    );
}

/**
 * Fetch safety net classification for a specific region
 */
export function fetchRegionSafetyNet(
    regionCode: string,
    signal?: AbortSignal,
): Promise<SafetyNetClassification> {
    return fetchJson(
        `${API_BASE}/regions/${encodeURIComponent(regionCode)}/safety-net`,
        { signal },
        'Failed to fetch safety net classification',
    );
}

// =============================================================================
// COMPOSITE TELEHEALTH STATUS
// =============================================================================

export interface TelehealthStatus {
    region_code: string;
    region_name: string;
    status: TelehealthStatusName;
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
export function fetchTelehealthStatus(
    regionCode: string,
    signal?: AbortSignal,
): Promise<TelehealthStatus> {
    return fetchJson(
        `${API_BASE}/regions/${encodeURIComponent(regionCode)}/telehealth-status`,
        { signal },
        'Failed to fetch telehealth status',
    );
}

// Bulk telehealth status for all regions
export interface RegionTelehealthStatus {
    region_code: string;
    region_name: string;
    lat: number;
    lon: number;
    status: TelehealthStatusName;
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
export function fetchAllTelehealthStatus(signal?: AbortSignal): Promise<AllTelehealthStatusResponse> {
    return fetchJson(
        `${API_BASE}/telehealth-status/all`,
        { signal },
        'Failed to fetch all telehealth status',
    );
}
