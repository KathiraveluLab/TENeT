import { useEffect, useMemo, useRef, useState } from 'react';
import { RegionSearchParams, RegionSummary, searchRegions } from '../api/catApi';

const SEARCH_DEBOUNCE_MS = 250;

export function useRegionSearch(params: RegionSearchParams) {
    const [results, setResults] = useState<RegionSummary[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const hasSearched = useRef(false);

    const stableParams = useMemo(() => JSON.stringify(params), [params]);

    useEffect(() => {
        let cancelled = false;
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
                cancelled = true;
            };
        }
        hasSearched.current = true;

        const timeoutId = window.setTimeout(async () => {
            try {
                setLoading(true);
                const data = await searchRegions(parsedParams);
                if (!cancelled) {
                    setResults(data);
                    setError(null);
                }
            } catch (err) {
                if (!cancelled) {
                    setError(err instanceof Error ? err.message : 'Failed to search regions');
                }
            } finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        }, SEARCH_DEBOUNCE_MS);

        return () => {
            cancelled = true;
            window.clearTimeout(timeoutId);
        };
    }, [stableParams]);

    return { results, loading, error };
}
