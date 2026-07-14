import { useEffect, useState } from 'react';
import { Season } from '../api/catApi';
import { fetchResearchProfiles } from '../api/researchApi';
import { ResearchProfile } from '../types/research';
import { errorMessage, isAbortError } from '../api/http';

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

        const controller = new AbortController();
        setLoading(true);
        setError(null);

        fetchResearchProfiles(codes, season, controller.signal)
            .then(data => {
                if (!controller.signal.aborted) {
                    setProfiles(data.profiles);
                    setMissingCodes(data.missing_codes);
                }
            })
            .catch((caught: unknown) => {
                if (!isAbortError(caught)) {
                    setProfiles([]);
                    setMissingCodes([]);
                    setError(errorMessage(caught, 'Failed to load comparison'));
                }
            })
            .finally(() => {
                if (!controller.signal.aborted) setLoading(false);
            });

        return () => {
            controller.abort();
        };
    }, [codesKey, season]);

    return { profiles, missingCodes, loading, error };
}
