import { Season, API_BASE } from './catApi';
import { ResearchProfile, ResearchProfilesResponse } from '../types/research';

export async function fetchResearchProfile(
    regionCode: string,
    season: Season = 'year_round',
): Promise<ResearchProfile> {
    const params = new URLSearchParams({ season });
    const response = await fetch(
        `${API_BASE}/regions/${encodeURIComponent(regionCode)}/research-profile?${params.toString()}`,
    );

    if (!response.ok) {
        throw new Error(response.status === 404 ? 'Community not found' : 'Failed to fetch research profile');
    }

    return response.json();
}

export async function fetchResearchProfiles(
    regionCodes: string[],
    season: Season = 'year_round',
): Promise<ResearchProfilesResponse> {
    const params = new URLSearchParams({
        codes: regionCodes.slice(0, 3).join(','),
        season,
    });
    const response = await fetch(`${API_BASE}/regions/research-profiles?${params.toString()}`);

    if (!response.ok) {
        throw new Error('Failed to fetch comparison profiles');
    }

    return response.json();
}
