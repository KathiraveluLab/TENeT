import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ALASKA_CENTER, ALASKA_ZOOM } from '../domain/mapUrlState';
import { BASELINE_THRESHOLDS } from '../types/scenario';
import { useMapUrlSync } from './useMapUrlSync';

const currentState = {
    selectedRegionCode: null,
    season: 'year_round' as const,
    mapMode: { type: 'cat' as const },
    pinnedRegionCodes: [],
    center: ALASKA_CENTER,
    zoom: ALASKA_ZOOM,
    scenario: { thresholds: BASELINE_THRESHOLDS, preset: null },
};

describe('useMapUrlSync', () => {
    it('restores the complete URL state on browser navigation', () => {
        window.history.replaceState(null, '', '/');
        const restoreState = vi.fn();
        renderHook(() => useMapUrlSync(currentState, restoreState));

        act(() => {
            window.history.pushState(null, '', '/?region=AK-2&season=winter&layer=gap&zoom=6');
            window.dispatchEvent(new PopStateEvent('popstate'));
        });

        expect(restoreState).toHaveBeenCalledWith(expect.objectContaining({
            selectedRegionCode: 'AK-2',
            season: 'winter',
            mapMode: { type: 'gapHunter' },
            zoom: 6,
        }));
    });
});
