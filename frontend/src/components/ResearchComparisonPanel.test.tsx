import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useComparisonProfiles } from '../hooks/useComparisonProfiles';
import type { ResearchProfile } from '../types/research';
import ResearchComparisonPanel from './ResearchComparisonPanel';

vi.mock('../hooks/useComparisonProfiles', () => ({
    useComparisonProfiles: vi.fn(),
}));

function buildProfile(overrides: Partial<ResearchProfile> & { code: string; name: string }): ResearchProfile {
    return {
        region: {
            region_code: overrides.code,
            name: overrides.name,
            lat: 61.2,
            lon: -149.9,
            region: 'Southcentral',
            population: 1000,
            cat_tier: 1,
            data_confidence: 'HIGH',
            has_data_gap: false,
            missing_fields: [],
            ...overrides.region,
        },
        connectivity: {
            fcc_coverage_25mbps_pct: 95.5,
            ookla_download_mbps: 120.4,
            ookla_upload_mbps: 24.2,
            latency_ms: 28,
            reliability_label: 'High',
            isp_name: 'GCI',
            data_source: 'Ookla',
            ...overrides.connectivity,
        },
        affordability: {
            monthly_cost: 125,
            median_income: 85000,
            burden_pct: 1.76,
            threshold_pct: 2.0,
            status: 'affordable',
            ...overrides.affordability,
        },
        healthcare: {
            nearest_facility_name: 'Alaska Regional',
            nearest_facility_distance_km: 5,
            nearest_facility_type: 'hospital',
            emergency_services: true,
            specialist_available: true,
            facility_count: 10,
            desert_score: 12.0,
            ...overrides.healthcare,
        },
        telehealth: {
            status: 'TELEHEALTH_READY',
            label: 'Telehealth Ready',
            video_feasible: true,
            audio_feasible: true,
            clinic_supported: true,
            season: 'year_round',
            season_note: 'Year-round baseline',
            ...overrides.telehealth,
        },
        methodology: {
            generated_at: '2026-01-01T00:00:00Z',
            sources: ['CAT', 'Ookla'],
            confidence_notes: [],
        },
    };
}

describe('ResearchComparisonPanel', () => {
    beforeEach(() => {
        vi.mocked(useComparisonProfiles).mockReturnValue({
            profiles: [
                buildProfile({ code: 'AK-1', name: 'Anchorage' }),
                buildProfile({
                    code: 'AK-2',
                    name: 'Bethel',
                    connectivity: {
                        fcc_coverage_25mbps_pct: 40.0,
                        ookla_download_mbps: 12.0,
                        ookla_upload_mbps: 2.1,
                        latency_ms: 88,
                        reliability_label: 'Moderate',
                        isp_name: 'Starlink',
                        data_source: 'Ookla',
                    },
                    affordability: {
                        monthly_cost: 450,
                        median_income: 52000,
                        burden_pct: 10.38,
                        threshold_pct: 2.0,
                        status: 'unaffordable',
                    },
                    healthcare: {
                        nearest_facility_name: 'Yukon-Kuskokwim Hospital',
                        nearest_facility_distance_km: 8,
                        nearest_facility_type: 'hospital',
                        emergency_services: true,
                        specialist_available: false,
                        facility_count: 1,
                        desert_score: 65.0,
                    },
                    telehealth: {
                        status: 'LIMITED_TELEHEALTH',
                        label: 'Limited Telehealth',
                        video_feasible: false,
                        audio_feasible: true,
                        clinic_supported: false,
                        season: 'year_round',
                        season_note: 'Year-round baseline',
                    },
                }),
            ],
            missingCodes: [],
            loading: false,
            error: null,
        });
    });

    it('renders status, affordability, clinic support, and full speed/FCC comparison rows', () => {
        render(
            <ResearchComparisonPanel
                pinnedRegionCodes={['AK-1', 'AK-2']}
                season="year_round"
                onSelectRegion={vi.fn()}
            />,
        );

        expect(screen.getByText('Telehealth status')).toBeInTheDocument();
        expect(screen.getByText('Telehealth Ready')).toBeInTheDocument();
        expect(screen.getByText('Limited Telehealth')).toBeInTheDocument();
        expect(screen.getByText('Affordability')).toBeInTheDocument();
        expect(screen.getByText('Affordable')).toBeInTheDocument();
        expect(screen.getByText('Unaffordable')).toBeInTheDocument();
        expect(screen.getByText('Clinic support')).toBeInTheDocument();
        expect(screen.getByText('Clinic supported')).toBeInTheDocument();
        expect(screen.getByText('No local clinic')).toBeInTheDocument();
        expect(screen.getByText('Upload')).toBeInTheDocument();
        expect(screen.getByText('Latency')).toBeInTheDocument();
        expect(screen.getByText('FCC 25 Mbps')).toBeInTheDocument();
    });
});

