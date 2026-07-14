import { useEffect, useMemo, useRef, useState } from 'react';
import { RegionSearchParams, RegionSummary, searchRegions } from '../api/catApi';
import { errorMessage, isAbortError } from '../api/http';

const SEARCH_DEBOUNCE_MS = 250;

export function useRegionSearch(params: RegionSearchParams) {
    const [results, setResults] = useState<RegionSummary[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const hasSearched = useRef(false);

    const stableParams = useMemo(() => JSON.stringify(params), [params]);

    useEffect(() => {
        const controller = new AbortController();
        const parsedParams = JSON.parse(stableParams) as RegionSearchParams;
        const hasActiveParams = Object.values(parsedParams).some(
            value => value !== undefined && value !== null && value !== '',
        );

        if (!hasActiveParams) {
            if (hasSearched.current) {
                setResults([]);
                setLoading(false);
                setError(null);
                hasSearched.current = false;
            }
            return () => {
                controller.abort();
            };
        }
        hasSearched.current = true;

        const timeoutId = window.setTimeout(async () => {
            try {
                setLoading(true);
                const data = await searchRegions(parsedParams, controller.signal);
                if (!controller.signal.aborted) {
                    setResults(data);
                    setError(null);
                }
            } catch (caught: unknown) {
                if (!isAbortError(caught)) {
                    setError(errorMessage(caught, 'Failed to search regions'));
                }
            } finally {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            }
        }, SEARCH_DEBOUNCE_MS);

        return () => {
            controller.abort();
            window.clearTimeout(timeoutId);
        };
    }, [stableParams]);

    return { results, loading, error };
}
