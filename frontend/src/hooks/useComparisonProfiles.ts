import { useEffect, useState } from 'react';
import { Season } from '../api/catApi';
import { fetchResearchProfiles } from '../api/researchApi';
import { ResearchProfile } from '../types/research';

export function useComparisonProfiles(regionCodes: string[], season: Season) {
    const codesKey = regionCodes.slice(0, 3).join(',');
    const [profiles, setProfiles] = useState<ResearchProfile[]>([]);
    const [missingCodes, setMissingCodes] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const codes = codesKey.split(',').filter(Boolean);
        if (codes.length < 2) {
            setProfiles([]);
            setMissingCodes([]);
            setError(null);
            setLoading(false);
            return;
        }

        let active = true;
        setLoading(true);
        setError(null);

        fetchResearchProfiles(codes, season)
            .then(data => {
                if (active) {
                    setProfiles(data.profiles);
                    setMissingCodes(data.missing_codes);
                }
            })
            .catch(err => {
                if (active) {
                    setProfiles([]);
                    setMissingCodes([]);
                    setError(err instanceof Error ? err.message : 'Failed to load comparison');
                }
            })
            .finally(() => {
                if (active) setLoading(false);
            });

        return () => {
            active = false;
        };
    }, [codesKey, season]);

    return { profiles, missingCodes, loading, error };
}
