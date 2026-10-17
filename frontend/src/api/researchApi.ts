import { Season, API_BASE } from './catApi';
import { ResearchProfile, ResearchProfilesResponse } from '../types/research';
import { fetchJson, withQuery } from './http';

export async function fetchResearchProfile(
    regionCode: string,
    season: Season = 'year_round',
    signal?: AbortSignal,
): Promise<ResearchProfile> {
    return fetchJson<ResearchProfile>(
        withQuery(`${API_BASE}/regions/${encodeURIComponent(regionCode)}/research-profile`, { season }),
        { signal },
        'Failed to fetch research profile',
    );
}

export async function fetchResearchProfiles(
    regionCodes: string[],
    season: Season = 'year_round',
    signal?: AbortSignal,
): Promise<ResearchProfilesResponse> {
    return fetchJson<ResearchProfilesResponse>(
        withQuery(`${API_BASE}/regions/research-profiles`, {
            codes: regionCodes.slice(0, 3).join(','),
            season,
        }),
        { signal },
        'Failed to fetch comparison profiles',
    );
}
