import { useEffect, useState } from 'react';
import { Season } from '../api/catApi';
import { fetchResearchProfile } from '../api/researchApi';
import { ResearchProfile } from '../types/research';
import { errorMessage, isAbortError } from '../api/http';

export function useResearchProfile(regionCode: string | null, season: Season) {
    const [profile, setProfile] = useState<ResearchProfile | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!regionCode) {
            setProfile(null);
            setError(null);
            setLoading(false);
            return;
        }

        const controller = new AbortController();
        setLoading(true);
        setProfile(null);
        setError(null);

        fetchResearchProfile(regionCode, season, controller.signal)
            .then(data => {
                if (!controller.signal.aborted) setProfile(data);
            })
            .catch((caught: unknown) => {
                if (!isAbortError(caught)) {
                    setProfile(null);
                    setError(errorMessage(caught, 'Failed to load research profile'));
                }
            })
            .finally(() => {
                if (!controller.signal.aborted) setLoading(false);
            });

        return () => {
            controller.abort();
        };
    }, [regionCode, season]);

    return { profile, loading, error };
}
