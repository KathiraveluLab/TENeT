/**
 * useScenarioPreview – fetches scenario preview with debounce, abort, and cache
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchScenarioPreview } from '../api/scenarioApi';
import type { Season } from '../api/catApi';
import type {
    ScenarioMode,
    ScenarioPreviewResponse,
    ScenarioThresholds,
} from '../types/scenario';

const DEBOUNCE_MS = 500;

function cacheKey(
    season: Season,
    thresholds: ScenarioThresholds,
    regionCodes: string[] | null,
): string {
    return JSON.stringify({ season, thresholds, regionCodes });
}

export interface ScenarioPreviewState {
    data: ScenarioPreviewResponse | null;
    loading: boolean;
    error: string | null;
}

export function useScenarioPreview(
    mode: ScenarioMode,
    thresholds: ScenarioThresholds,
    season: Season,
    regionCodes: string[] | null = null,
    setMode?: (mode: ScenarioMode) => void,
): ScenarioPreviewState {
    const [data, setData] = useState<ScenarioPreviewResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const cacheRef = useRef<Map<string, ScenarioPreviewResponse>>(new Map());
    const abortRef = useRef<AbortController | null>(null);
    const timerRef = useRef<number | null>(null);

    const fetchPreview = useCallback(async (
        currentThresholds: ScenarioThresholds,
        currentSeason: Season,
        currentRegionCodes: string[] | null,
    ) => {
        const key = cacheKey(currentSeason, currentThresholds, currentRegionCodes);

        // Check cache
        const cached = cacheRef.current.get(key);
        if (cached) {
            setData(cached);
            setLoading(false);
            setError(null);
            setMode?.('active');
            return;
        }

        // Abort previous
        abortRef.current?.abort();
        const controller = new AbortController();
        abortRef.current = controller;

        setLoading(true);
        setError(null);
        setMode?.('calculating');

        try {
            const result = await fetchScenarioPreview(
                {
                    mode: 'preview',
                    season: currentSeason,
                    thresholds: currentThresholds,
                    region_codes: currentRegionCodes,
                },
                controller.signal,
            );

            if (!controller.signal.aborted) {
                cacheRef.current.set(key, result);
                // Keep cache bounded
                if (cacheRef.current.size > 20) {
                    const firstKey = cacheRef.current.keys().next().value;
                    if (firstKey !== undefined) {
                        cacheRef.current.delete(firstKey);
                    }
                }
                setData(result);
                setLoading(false);
                setError(null);
                setMode?.('active');
            }
        } catch (err: any) {
            if (err?.name === 'AbortError') return;
            if (!controller.signal.aborted) {
                setError(err?.message || 'Scenario preview failed');
                setLoading(false);
                setMode?.('active');
            }
        }
    }, [setMode]);

    // Debounced fetch
    useEffect(() => {
        if (mode === 'off') {
            setData(null);
            setError(null);
            setLoading(false);
            abortRef.current?.abort();
            if (timerRef.current) {
                window.clearTimeout(timerRef.current);
                timerRef.current = null;
            }
            return;
        }

        if (timerRef.current) {
            window.clearTimeout(timerRef.current);
        }

        timerRef.current = window.setTimeout(() => {
            fetchPreview(thresholds, season, regionCodes);
        }, DEBOUNCE_MS);

        return () => {
            if (timerRef.current) {
                window.clearTimeout(timerRef.current);
                timerRef.current = null;
            }
        };
    }, [mode, thresholds, season, regionCodes, fetchPreview]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            abortRef.current?.abort();
            if (timerRef.current) window.clearTimeout(timerRef.current);
        };
    }, []);

    return { data, loading, error };
}
