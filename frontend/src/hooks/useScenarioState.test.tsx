import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BASELINE_THRESHOLDS } from '../types/scenario';
import { useScenarioState } from './useScenarioState';

describe('useScenarioState restoration', () => {
    it('restores scenario state supplied by URL ownership and resets when deactivated', () => {
        const { result } = renderHook(() => useScenarioState('year_round', {
            active: true,
            thresholds: {
                min_download_mbps: 100,
                min_upload_mbps: 20,
                max_latency_ms: 90,
                affordability_burden_pct: 4,
                clinic_proximity_km: 30,
            },
            preset: 'equity',
        }));

        expect(result.current.mode).toBe('active');
        expect(result.current.thresholds.min_download_mbps).toBe(100);
        expect(result.current.thresholds.min_upload_mbps).toBe(20);
        expect(result.current.thresholds.max_latency_ms).toBe(90);
        expect(result.current.thresholds.affordability_burden_pct).toBe(4);
        expect(result.current.thresholds.clinic_proximity_km).toBe(30);

        act(() => {
            result.current.deactivate();
        });

        expect(result.current.mode).toBe('off');
        expect(result.current.thresholds).toEqual(BASELINE_THRESHOLDS);
        expect(result.current.activePreset).toBeNull();
    });
});
