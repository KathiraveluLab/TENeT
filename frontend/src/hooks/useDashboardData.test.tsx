import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
    fetchAffordability,
    fetchAllTelehealthStatus,
    fetchDataGapsSummary,
    fetchHealthcareSummary,
    fetchPerformanceSummary,
    fetchStatistics,
} from '../api/catApi';
import { useDashboardData } from './useDashboardData';

vi.mock('../api/catApi', () => ({
    fetchAffordability: vi.fn(),
    fetchAllTelehealthStatus: vi.fn(),
    fetchDataGapsSummary: vi.fn(),
    fetchHealthcareSummary: vi.fn(),
    fetchPerformanceSummary: vi.fn(),
    fetchStatistics: vi.fn(),
}));

const mockedFetchStatistics = vi.mocked(fetchStatistics);
const mockedFetchTelehealth = vi.mocked(fetchAllTelehealthStatus);
const mockedFetchHealthcare = vi.mocked(fetchHealthcareSummary);
const mockedFetchPerformance = vi.mocked(fetchPerformanceSummary);
const mockedFetchDataGaps = vi.mocked(fetchDataGapsSummary);
const mockedFetchAffordability = vi.mocked(fetchAffordability);

beforeEach(() => {
    vi.clearAllMocks();
    mockedFetchStatistics.mockResolvedValue({
        total_regions: 4,
        total_data_points: 10,
        total_uploads: 1,
        completed_uploads: 1,
        total_gating_rules: 0,
        active_gating_rules: 0,
        total_healthcare_sites: 2,
        hospitals: 1,
        clinics: 1,
    });
    mockedFetchTelehealth.mockResolvedValue({
        regions: [],
        count: 4,
        summary: {
            telehealth_ready: 1,
            community_anchor: 1,
            critical_gap: 1,
            data_unavailable: 1,
        },
    });
    mockedFetchHealthcare.mockResolvedValue({
        total_facilities: 2,
        by_type: { hospital: 1, clinic: 1, pharmacy: 0, health_center: 0 },
        features: { with_emergency: 1, with_specialists: 0, with_telehealth: 1 },
        data_source: 'test',
    });
    mockedFetchPerformance.mockResolvedValue({
        has_data: true,
        period: { year: 2025, quarter: 1, label: '2025 Q1' },
        coverage: { total_tiles: 1, tiles_with_speed_data: 1, total_tests: 1, total_devices: 1 },
        speeds: { avg_download_mbps: 25, max_download_mbps: 25, min_download_mbps: 25, median_download_mbps: 25 },
        distribution: { excellent: 0, good: 1, moderate: 0, poor: 0, critical: 0 },
        telehealth_viable_pct: 100,
    });
    mockedFetchDataGaps.mockResolvedValue({
        total_places: 1,
        places_with_gaps: 0,
        gap_breakdown: {},
        confidence_distribution: { HIGH: 1, MEDIUM: 0, LOW: 0 },
        telehealth_viability: { YES: 1, NO: 0, UNCERTAIN: 0 },
        primary_access: { WIRED: 1, SATELLITE: 0, LIMITED: 0 },
    });
    mockedFetchAffordability.mockResolvedValue({
        zones: [],
        count: 1,
        monthly_cost: 120,
        threshold_pct: 2,
        summary: { affordable: 1, unaffordable: 0, affordable_pct: 100 },
    });
});

describe('useDashboardData', () => {
    it('keeps fulfilled sections and identifies a rejected section', async () => {
        mockedFetchPerformance.mockRejectedValue(new Error('Performance period unavailable'));

        const { result } = renderHook(() => useDashboardData());

        await waitFor(() => expect(result.current.loading).toBe(false));

        expect(result.current.data.statistics?.total_regions).toBe(4);
        expect(result.current.data.performance).toBeNull();
        expect(result.current.sectionErrors).toEqual({
            performance: 'Performance period unavailable',
        });
        expect(result.current.availableSectionCount).toBe(5);
        expect(result.current.hasPartialData).toBe(true);
        expect(result.current.error).toBeNull();
    });

    it('passes one request signal to every dashboard source and aborts on unmount', async () => {
        const { result, unmount } = renderHook(() => useDashboardData());
        await waitFor(() => expect(result.current.loading).toBe(false));

        const signal = mockedFetchStatistics.mock.calls[0][0];
        expect(signal).toBeInstanceOf(AbortSignal);
        expect(mockedFetchTelehealth).toHaveBeenCalledWith(signal);
        expect(mockedFetchHealthcare).toHaveBeenCalledWith(signal);
        expect(mockedFetchPerformance).toHaveBeenCalledWith(signal);
        expect(mockedFetchDataGaps).toHaveBeenCalledWith(signal);
        expect(mockedFetchAffordability).toHaveBeenCalledWith(120, 2, signal);

        unmount();
        expect(signal?.aborted).toBe(true);
    });
});
