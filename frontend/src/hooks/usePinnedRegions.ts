import { useCallback, useEffect, useState } from 'react';

const PINNED_REGIONS_KEY = 'tenet:pinned-regions';
const MAX_PINNED_REGIONS = 3;

function readPinnedRegions(): string[] {
    try {
        const raw = window.localStorage.getItem(PINNED_REGIONS_KEY);
        const parsed = raw ? JSON.parse(raw) : [];
        return Array.isArray(parsed) ? parsed.filter(code => typeof code === 'string') : [];
    } catch {
        return [];
    }
}

export function usePinnedRegions(initialPinnedRegionCodes?: string[]) {
    const [pinnedRegionCodes, setPinnedRegionCodes] = useState<string[]>(
        () => (initialPinnedRegionCodes?.length ? initialPinnedRegionCodes : readPinnedRegions())
            .slice(0, MAX_PINNED_REGIONS)
    );

    useEffect(() => {
        window.localStorage.setItem(PINNED_REGIONS_KEY, JSON.stringify(pinnedRegionCodes));
    }, [pinnedRegionCodes]);

    const isPinned = useCallback(
        (regionCode: string) => pinnedRegionCodes.includes(regionCode),
        [pinnedRegionCodes],
    );

    const togglePinned = useCallback((regionCode: string) => {
        setPinnedRegionCodes(current => {
            if (current.includes(regionCode)) {
                return current.filter(code => code !== regionCode);
            }
            if (current.length >= MAX_PINNED_REGIONS) {
                return current;
            }
            return [...current, regionCode];
        });
    }, []);

    const replacePinned = useCallback((regionCodes: string[]) => {
        const uniqueCodes = regionCodes.filter((code, index) => (
            typeof code === 'string' && code && regionCodes.indexOf(code) === index
        ));
        setPinnedRegionCodes(uniqueCodes.slice(0, MAX_PINNED_REGIONS));
    }, []);

    return {
        pinnedRegionCodes,
        isPinned,
        togglePinned,
        replacePinned,
        maxPinnedRegions: MAX_PINNED_REGIONS,
    };
}
