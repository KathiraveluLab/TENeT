/**
 * useScenarioState – manages scenario thresholds and presets.
 */
import { useCallback, useMemo, useState } from 'react';
import type { Season } from '../api/catApi';
import {
    BASELINE_THRESHOLDS,
    SCENARIO_PRESETS,
    type ScenarioMode,
    type ScenarioThresholds,
} from '../types/scenario';

function thresholdsEqual(a: ScenarioThresholds, b: ScenarioThresholds): boolean {
    return (
        a.min_download_mbps === b.min_download_mbps &&
        a.min_upload_mbps === b.min_upload_mbps &&
        a.max_latency_ms === b.max_latency_ms &&
        a.clinic_proximity_km === b.clinic_proximity_km &&
        a.affordability_burden_pct === b.affordability_burden_pct
    );
}

export interface ScenarioUrlState {
    active: boolean;
    thresholds: Partial<ScenarioThresholds>;
    preset: string | null;
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
    /** Restore scenario state from browser navigation. */
    restoreFromUrl: (state: ScenarioUrlState) => void;
}

const EMPTY_SCENARIO_URL_STATE: ScenarioUrlState = {
    active: false,
    thresholds: {},
    preset: null,
};

export function useScenarioState(
    _season: Season,
    initialUrl: ScenarioUrlState = EMPTY_SCENARIO_URL_STATE,
): ScenarioState {
    const [mode, setMode] = useState<ScenarioMode>(initialUrl.active ? 'active' : 'off');
    const [thresholds, setThresholds] = useState<ScenarioThresholds>(() => ({
        ...BASELINE_THRESHOLDS,
        ...initialUrl.thresholds,
    }));
    const [activePreset, setActivePreset] = useState<string | null>(initialUrl.preset);

    const isBaselineEquivalent = useMemo(
        () => thresholdsEqual(thresholds, BASELINE_THRESHOLDS),
        [thresholds],
    );

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
            setThresholds({ ...BASELINE_THRESHOLDS, ...preset.thresholds });
            setActivePreset(presetId);
        }
    }, []);

    const resetToBaseline = useCallback(() => {
        setThresholds({ ...BASELINE_THRESHOLDS });
        setActivePreset('baseline');
    }, []);

    const restoreFromUrl = useCallback((state: ScenarioUrlState) => {
        setMode(state.active ? 'active' : 'off');
        setThresholds({ ...BASELINE_THRESHOLDS, ...state.thresholds });
        setActivePreset(state.preset);
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
        restoreFromUrl,
    };
}
