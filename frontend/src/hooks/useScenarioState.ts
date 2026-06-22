/**
 * useScenarioState – manages scenario thresholds, presets, and URL state
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Season } from '../api/catApi';
import {
    BASELINE_THRESHOLDS,
    SCENARIO_PRESETS,
    type ScenarioMode,
    type ScenarioPreset,
    type ScenarioThresholds,
} from '../types/scenario';

const URL_SYNC_DEBOUNCE_MS = 300;

function thresholdsEqual(a: ScenarioThresholds, b: ScenarioThresholds): boolean {
    return (
        a.min_download_mbps === b.min_download_mbps &&
        a.min_upload_mbps === b.min_upload_mbps &&
        a.max_latency_ms === b.max_latency_ms &&
        a.clinic_proximity_km === b.clinic_proximity_km &&
        a.affordability_burden_pct === b.affordability_burden_pct
    );
}

function parseScenarioUrlParams(): {
    active: boolean;
    thresholds: Partial<ScenarioThresholds>;
    preset: string | null;
} {
    if (typeof window === 'undefined') {
        return { active: false, thresholds: {}, preset: null };
    }

    const params = new URLSearchParams(window.location.search);
    if (params.get('scenario') !== '1') {
        return { active: false, thresholds: {}, preset: null };
    }

    const partial: Partial<ScenarioThresholds> = {};
    const bd = params.get('bd');
    if (bd !== null && !isNaN(Number(bd))) partial.min_download_mbps = Number(bd);
    const up = params.get('up');
    if (up !== null && !isNaN(Number(up))) partial.min_upload_mbps = Number(up);
    const latency = params.get('latency');
    if (latency !== null) {
        if (latency === 'baseline') {
            partial.max_latency_ms = null;
        } else if (!isNaN(Number(latency))) {
            partial.max_latency_ms = Number(latency);
        }
    }
    const aff = params.get('aff');
    if (aff !== null && !isNaN(Number(aff))) partial.affordability_burden_pct = Number(aff);
    const clinic = params.get('clinic');
    if (clinic !== null && clinic !== 'baseline') {
        if (!isNaN(Number(clinic))) partial.clinic_proximity_km = Number(clinic);
    }

    return {
        active: true,
        thresholds: partial,
        preset: params.get('preset'),
    };
}

export interface ScenarioState {
    mode: ScenarioMode;
    thresholds: ScenarioThresholds;
    activePreset: string | null;
    isBaselineEquivalent: boolean;

    /** Turn scenario mode on */
    activate: () => void;
    /** Turn scenario mode off and clean URL params */
    deactivate: () => void;
    /** Update a single threshold value */
    setThreshold: <K extends keyof ScenarioThresholds>(key: K, value: ScenarioThresholds[K]) => void;
    /** Apply a preset */
    applyPreset: (presetId: string) => void;
    /** Reset to baseline */
    resetToBaseline: () => void;
    /** Set mode directly (e.g. for 'calculating') */
    setMode: (mode: ScenarioMode) => void;
}

export function useScenarioState(season: Season): ScenarioState {
    const initialUrl = useMemo(() => parseScenarioUrlParams(), []);

    const [mode, setMode] = useState<ScenarioMode>(initialUrl.active ? 'active' : 'off');
    const [thresholds, setThresholds] = useState<ScenarioThresholds>(() => ({
        ...BASELINE_THRESHOLDS,
        ...initialUrl.thresholds,
    }));
    const [activePreset, setActivePreset] = useState<string | null>(initialUrl.preset);
    const urlSyncTimerRef = useRef<number | null>(null);

    const isBaselineEquivalent = useMemo(
        () => thresholdsEqual(thresholds, BASELINE_THRESHOLDS),
        [thresholds],
    );

    // ── URL state sync ─────────────────────────────────────────────────
    useEffect(() => {
        if (typeof window === 'undefined') return;

        if (urlSyncTimerRef.current) {
            window.clearTimeout(urlSyncTimerRef.current);
        }

        urlSyncTimerRef.current = window.setTimeout(() => {
            const params = new URLSearchParams(window.location.search);

            // Remove all scenario params first
            params.delete('scenario');
            params.delete('bd');
            params.delete('up');
            params.delete('latency');
            params.delete('aff');
            params.delete('clinic');
            params.delete('preset');

            if (mode !== 'off') {
                params.set('scenario', '1');
                params.set('bd', String(thresholds.min_download_mbps));
                params.set('up', String(thresholds.min_upload_mbps));
                if (thresholds.max_latency_ms !== null) {
                    params.set('latency', String(thresholds.max_latency_ms));
                } else {
                    params.set('latency', 'baseline');
                }
                params.set('aff', String(thresholds.affordability_burden_pct));
                if (thresholds.clinic_proximity_km !== null) {
                    params.set('clinic', String(thresholds.clinic_proximity_km));
                } else {
                    params.set('clinic', 'baseline');
                }
                if (activePreset) params.set('preset', activePreset);
            }

            const nextUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ''}`;
            window.history.replaceState(null, '', nextUrl);
            urlSyncTimerRef.current = null;
        }, URL_SYNC_DEBOUNCE_MS);

        return () => {
            if (urlSyncTimerRef.current) {
                window.clearTimeout(urlSyncTimerRef.current);
                urlSyncTimerRef.current = null;
            }
        };
    }, [mode, thresholds, activePreset]);

    // ── Actions ────────────────────────────────────────────────────────
    const activate = useCallback(() => setMode('active'), []);

    const deactivate = useCallback(() => {
        setMode('off');
        setThresholds({ ...BASELINE_THRESHOLDS });
        setActivePreset(null);
    }, []);

    const setThreshold = useCallback(<K extends keyof ScenarioThresholds>(
        key: K,
        value: ScenarioThresholds[K],
    ) => {
        setThresholds(prev => ({ ...prev, [key]: value }));
        setActivePreset(null); // Clear preset when user manually adjusts
    }, []);

    const applyPreset = useCallback((presetId: string) => {
        if (presetId === 'baseline') {
            setThresholds({ ...BASELINE_THRESHOLDS });
            setActivePreset('baseline');
            return;
        }
        const preset = SCENARIO_PRESETS.find(p => p.id === presetId);
        if (preset) {
            setThresholds(prev => ({ ...BASELINE_THRESHOLDS, ...preset.thresholds }));
            setActivePreset(presetId);
        }
    }, []);

    const resetToBaseline = useCallback(() => {
        setThresholds({ ...BASELINE_THRESHOLDS });
        setActivePreset('baseline');
    }, []);

    return {
        mode,
        thresholds,
        activePreset,
        isBaselineEquivalent,
        activate,
        deactivate,
        setThreshold,
        applyPreset,
        resetToBaseline,
        setMode,
    };
}
