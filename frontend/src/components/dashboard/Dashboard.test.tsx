import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useDashboardData, type DashboardData } from '../../hooks/useDashboardData';
import Dashboard from './Dashboard';

vi.mock('../../hooks/useDashboardData', () => ({
    useDashboardData: vi.fn(),
}));

const dashboardData: DashboardData = {
    statistics: {
        total_regions: 2,
        total_data_points: 20,
        total_uploads: 5,
        completed_uploads: 5,
        total_gating_rules: 2,
        active_gating_rules: 2,
        total_healthcare_sites: 4,
        hospitals: 1,
        clinics: 2,
    },
    telehealthStatus: {
        count: 2,
        summary: {
            telehealth_ready: 1,
            community_anchor: 0,
            critical_gap: 1,
            data_unavailable: 0,
        },
        regions: [
            {
                region_code: 'AK-CRITICAL',
                region_name: 'Critical Community',
                lat: 60,
                lon: -150,
                status: 'CRITICAL_GAP',
                color: '#b42318',
                internet_cost: 120,
                isp_name: 'Provider',
                burden_pct: 3.2,
                median_income: 40000,
                has_nearby_clinic: false,
                nearest_clinic_name: null,
                nearest_clinic_km: null,
                access_mode: 'air',
                recommendation: 'Prioritize connectivity and supported care access.',
            },
        ],
    },
    healthcare: {
        total_facilities: 4,
        by_type: { hospital: 1, clinic: 2, pharmacy: 0, health_center: 1 },
        features: { with_emergency: 1, with_specialists: 1, with_telehealth: 2 },
        data_source: 'Test inventory',
    },
    performance: {
        has_data: true,
        period: { year: 2025, quarter: 4, label: 'Q4 2025' },
        coverage: { total_tiles: 10, tiles_with_speed_data: 8, total_tests: 100, total_devices: 40 },
        speeds: { avg_download_mbps: 24, max_download_mbps: 80, min_download_mbps: 2, median_download_mbps: 20 },
        distribution: { excellent: 2, good: 2, moderate: 2, poor: 1, critical: 1 },
        telehealth_viable_pct: 50,
    },
    dataGaps: {
        total_places: 10,
        places_with_gaps: 3,
        gap_breakdown: {},
        confidence_distribution: { HIGH: 6, MEDIUM: 3, LOW: 1 },
        telehealth_viability: { YES: 5, NO: 2, UNCERTAIN: 3 },
        primary_access: { WIRED: 7, SATELLITE: 2, LIMITED: 1 },
    },
    affordability: {
        zones: [],
        count: 10,
        monthly_cost: 120,
        threshold_pct: 2,
        summary: { affordable: 6, unaffordable: 4, affordable_pct: 60 },
    },
};

describe('Statewide Insights', () => {
    beforeEach(() => {
        vi.mocked(useDashboardData).mockReturnValue({
            data: dashboardData,
            sectionErrors: {},
            availableSectionCount: 6,
            hasPartialData: false,
            loading: false,
            error: null,
        });
    });

    it('uses accurate affordability and satellite-dependency labels', () => {
        render(<Dashboard onClose={vi.fn()} />);

        expect(screen.getByRole('heading', { name: 'Statewide Insights' })).toBeInTheDocument();
        expect(screen.getByText('Unaffordable analyzed zones')).toBeInTheDocument();
        expect(screen.getByText('Satellite-primary places')).toBeInTheDocument();
        expect(screen.getByText(/not a measure of affordability/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Open telehealth access map' })).toBeInTheDocument();
        expect(screen.queryByText('Unaffordable Areas')).not.toBeInTheDocument();
    });

    it('routes section and community actions back to the map', () => {
        const onViewMap = vi.fn();
        const onViewRegion = vi.fn();
        render(
            <Dashboard
                onClose={vi.fn()}
                onViewMap={onViewMap}
                onViewRegion={onViewRegion}
            />,
        );

        fireEvent.click(screen.getByRole('button', { name: 'Open Gap Hunter' }));
        expect(onViewMap).toHaveBeenCalledWith('gap');

        fireEvent.click(screen.getByRole('button', { name: 'View on map' }));
        expect(onViewRegion).toHaveBeenCalledWith('AK-CRITICAL');
    });
});
