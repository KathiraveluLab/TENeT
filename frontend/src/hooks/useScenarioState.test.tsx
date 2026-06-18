import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BASELINE_THRESHOLDS } from '../types/scenario';
import { useScenarioState } from './useScenarioState';

describe('useScenarioState URL sync', () => {
    it('restores scenario params and removes them when scenario mode is deactivated', async () => {
        window.history.replaceState(null, '', '/?scenario=1&bd=100&up=20&aff=4&clinic=30&preset=equity');

        const { result } = renderHook(() => useScenarioState('year_round'));

        expect(result.current.mode).toBe('active');
        expect(result.current.thresholds.min_download_mbps).toBe(100);
        expect(result.current.thresholds.min_upload_mbps).toBe(20);
        expect(result.current.thresholds.affordability_burden_pct).toBe(4);
        expect(result.current.thresholds.clinic_proximity_km).toBe(30);

        act(() => {
            result.current.setThreshold('min_download_mbps', 75);
        });

        await waitFor(() => {
            expect(new URLSearchParams(window.location.search).get('bd')).toBe('75');
        });

        act(() => {
            result.current.deactivate();
        });

        await waitFor(() => {
            const params = new URLSearchParams(window.location.search);
            expect(params.has('scenario')).toBe(false);
            expect(params.has('bd')).toBe(false);
        });
        expect(result.current.thresholds).toEqual(BASELINE_THRESHOLDS);
    });
});
