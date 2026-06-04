import { useEffect, useState } from 'react';
import { fetchRegionSummary, RegionSummary } from '../api/catApi';

export function useRegionSummary() {
    const [regions, setRegions] = useState<RegionSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;

        async function loadSummary() {
            try {
                setLoading(true);
                const data = await fetchRegionSummary();
                if (!cancelled) {
                    setRegions(data);
                    setError(null);
                }
            } catch (err) {
                if (!cancelled) {
                    setError(err instanceof Error ? err.message : 'Failed to load region summary');
                }
            } finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        }

        loadSummary();

        return () => {
            cancelled = true;
        };
    }, []);

    return { regions, loading, error };
}
