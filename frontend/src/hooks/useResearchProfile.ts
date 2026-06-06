import { useEffect, useState } from 'react';
import { Season } from '../api/catApi';
import { fetchResearchProfile } from '../api/researchApi';
import { ResearchProfile } from '../types/research';

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

        let active = true;
        setLoading(true);
        setError(null);

        fetchResearchProfile(regionCode, season)
            .then(data => {
                if (active) setProfile(data);
            })
            .catch(err => {
                if (active) {
                    setProfile(null);
                    setError(err instanceof Error ? err.message : 'Failed to load research profile');
                }
            })
            .finally(() => {
                if (active) setLoading(false);
            });

        return () => {
            active = false;
        };
    }, [regionCode, season]);

    return { profile, loading, error };
}
