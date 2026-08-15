import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchScenarioPreview } from '../api/scenarioApi';
import { BASELINE_THRESHOLDS, type ScenarioPreviewResponse } from '../types/scenario';
import { useScenarioPreview } from './useScenarioPreview';

vi.mock('../api/scenarioApi', () => ({
    fetchScenarioPreview: vi.fn(),
}));

const preview: ScenarioPreviewResponse = {
    scenario: {
        season: 'year_round',
        thresholds: BASELINE_THRESHOLDS,
        is_baseline_equivalent: true,
    },
    summary: {
        total_regions: 1,
        status_changed_regions: 0,
        improved_count: 0,
        worsened_count: 0,
        unchanged_count: 1,
        telehealth_ready: 1,
        community_anchor: 0,
        limited_telehealth: 0,
        critical_gap: 0,
        data_unavailable: 0,
    },
    regions: [],
};

describe('useScenarioPreview', () => {
    afterEach(() => {
        vi.useRealTimers();
        vi.clearAllMocks();
    });

    it('clears stale output immediately when assumptions change or the refresh fails', async () => {
        vi.useFakeTimers();
        vi.mocked(fetchScenarioPreview)
            .mockResolvedValueOnce(preview)
            .mockRejectedValueOnce(new Error('Preview unavailable'));
        const setMode = vi.fn();

        const { result, rerender } = renderHook(
            ({ thresholds }) => useScenarioPreview(
                'active',
                thresholds,
                'year_round',
                null,
                setMode,
            ),
            { initialProps: { thresholds: BASELINE_THRESHOLDS } },
        );

        await act(async () => {
            await vi.advanceTimersByTimeAsync(500);
            await Promise.resolve();
        });
        expect(result.current.data).toEqual(preview);

        rerender({ thresholds: { ...BASELINE_THRESHOLDS, min_download_mbps: 75 } });
        expect(result.current.data).toBeNull();
        expect(result.current.loading).toBe(true);

        await act(async () => {
            await vi.advanceTimersByTimeAsync(500);
            await Promise.resolve();
        });
        expect(result.current.data).toBeNull();
        expect(result.current.error).toBe('Preview unavailable');
    });
});
