import { useEffect, useState } from 'react';
import { fetchRegionSummary, RegionSummary } from '../api/catApi';
import { errorMessage, isAbortError } from '../api/http';

export function useRegionSummary() {
    const [regions, setRegions] = useState<RegionSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const controller = new AbortController();

        async function loadSummary() {
            try {
                setLoading(true);
                const data = await fetchRegionSummary(controller.signal);
                if (!controller.signal.aborted) {
                    setRegions(data);
                    setError(null);
                }
            } catch (caught: unknown) {
                if (!isAbortError(caught)) {
                    setError(errorMessage(caught, 'Failed to load region summary'));
                }
            } finally {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            }
        }

        loadSummary();

        return () => {
            controller.abort();
        };
    }, []);

    return { regions, loading, error };
}
