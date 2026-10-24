import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BASELINE_THRESHOLDS } from '../types/scenario';
import { useScenarioState } from './useScenarioState';

describe('useScenarioState', () => {
    it('owns thresholds while accepting initial and restored URL state', () => {
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
            result.current.setThreshold('min_download_mbps', 75);
            result.current.setThreshold('max_latency_ms', 120);
        });

        expect(result.current.thresholds.min_download_mbps).toBe(75);
        expect(result.current.thresholds.max_latency_ms).toBe(120);
        expect(result.current.activePreset).toBeNull();

        act(() => {
            result.current.restoreFromUrl({
                active: false,
                thresholds: {},
                preset: null,
            });
        });

        expect(result.current.mode).toBe('off');
        expect(result.current.thresholds).toEqual(BASELINE_THRESHOLDS);
        expect(result.current.activePreset).toBeNull();
    });

    it('applies scenario presets in research parity with the paper', () => {
        const { result } = renderHook(() => useScenarioState('year_round'));

        // Broadband Equity Goal
        act(() => {
            result.current.applyPreset('equity');
        });
        expect(result.current.activePreset).toBe('equity');
        expect(result.current.thresholds).toEqual({
            min_download_mbps: 100,
            min_upload_mbps: 20,
            max_latency_ms: 100,
            affordability_burden_pct: 2,
            clinic_proximity_km: null,
        });

        // Universal Clinic Access
        act(() => {
            result.current.applyPreset('clinic_access');
        });
        expect(result.current.activePreset).toBe('clinic_access');
        expect(result.current.thresholds).toEqual({
            min_download_mbps: 25,
            min_upload_mbps: 3,
            max_latency_ms: 150,
            affordability_burden_pct: 2,
            clinic_proximity_km: 15,
        });

        // FCC Standard
        act(() => {
            result.current.applyPreset('fcc');
        });
        expect(result.current.activePreset).toBe('fcc');
        expect(result.current.thresholds).toEqual({
            min_download_mbps: 25,
            min_upload_mbps: 3,
            max_latency_ms: 150,
            affordability_burden_pct: 2,
            clinic_proximity_km: null,
        });
    });
});
