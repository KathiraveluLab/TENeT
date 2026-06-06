import { Season } from '../api/catApi';

export type DataConfidence = 'HIGH' | 'MEDIUM' | 'LOW' | 'MISSING' | string;

export interface ResearchProfile {
    region: {
        region_code: string;
        name: string;
        lat: number | null;
        lon: number | null;
        region: string | null;
        cat_tier: number | null;
        data_confidence: DataConfidence;
        has_data_gap: boolean;
        missing_fields: string[];
    };
    connectivity: {
        fcc_coverage_25mbps_pct: number | null;
        ookla_download_mbps: number | null;
        ookla_upload_mbps: number | null;
        latency_ms: number | null;
        reliability_label: string | null;
        isp_name: string | null;
        data_source: string | null;
    };
    affordability: {
        monthly_cost: number | null;
        median_income: number | null;
        burden_pct: number | null;
        threshold_pct: number | null;
        status: 'affordable' | 'unaffordable' | 'unknown';
    };
    healthcare: {
        nearest_facility_name: string | null;
        nearest_facility_distance_km: number | null;
        nearest_facility_type: string | null;
        emergency_services: boolean | null;
        specialist_available: boolean | null;
        facility_count: number | null;
        desert_score: number | null;
    };
    telehealth: {
        status: string;
        label: string;
        video_feasible: boolean | null;
        audio_feasible: boolean | null;
        clinic_supported: boolean | null;
        season: Season;
        season_note: string;
    };
    methodology: {
        generated_at: string;
        sources: string[];
        confidence_notes: string[];
    };
}

export interface ResearchProfilesResponse {
    profiles: ResearchProfile[];
    count: number;
    missing_codes: string[];
    season: Season;
}
