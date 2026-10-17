import { describe, expect, it } from 'vitest';
import { BASELINE_THRESHOLDS } from '../types/scenario';
import {
    ALASKA_CENTER,
    ALASKA_ZOOM,
    parseMapUrlState,
    serializeMapUrlState,
} from './mapUrlState';

describe('map URL state', () => {
    it('parses selection, viewport, layer, pins, and season', () => {
        const state = parseMapUrlState(
            '?region=AK-1&season=winter&layer=gap&pins=AK-1,AK-2&lat=64.5&lng=-151.25&zoom=7',
        );

        expect(state).toMatchObject({
            selectedRegionCode: 'AK-1',
            season: 'winter',
            mapMode: { type: 'gapHunter' },
            pinnedRegionCodes: ['AK-1', 'AK-2'],
            center: [64.5, -151.25],
            zoom: 7,
        });
    });

    it('falls back for invalid or stale viewport values', () => {
        expect(parseMapUrlState('?season=invalid&layer=unknown&lat=200&lng=nope&zoom=99')).toMatchObject({
            season: 'year_round',
            mapMode: { type: 'cat' },
            center: ALASKA_CENTER,
            zoom: ALASKA_ZOOM,
        });
        expect(parseMapUrlState('?lat=62.9752&lng=-154.95117&zoom=4')).toMatchObject({
            center: ALASKA_CENTER,
            zoom: ALASKA_ZOOM,
        });
    });

    it('round-trips scenario mode and threshold parameters', () => {
        const search = serializeMapUrlState('?unrelated=kept', {
            selectedRegionCode: 'AK-9',
            season: 'summer',
            mapMode: { type: 'scenario' },
            pinnedRegionCodes: [],
            center: ALASKA_CENTER,
            zoom: ALASKA_ZOOM,
            scenario: {
                thresholds: { ...BASELINE_THRESHOLDS, min_download_mbps: 100, max_latency_ms: null },
                preset: 'equity',
            },
        });
        const parsed = parseMapUrlState(`?${search}`);

        expect(new URLSearchParams(search).get('unrelated')).toBe('kept');
        expect(parsed.mapMode).toEqual({ type: 'scenario' });
        expect(parsed.scenario).toEqual({
            thresholds: {
                min_download_mbps: 100,
                min_upload_mbps: 3,
                max_latency_ms: null,
                affordability_burden_pct: 2,
                clinic_proximity_km: null,
            },
            preset: 'equity',
        });
    });

    it('removes stale owned parameters when returning to CAT mode', () => {
        const search = serializeMapUrlState(
            '?layer=gap&scenario=1&bd=100&preset=equity&external=1',
            {
                selectedRegionCode: null,
                season: 'year_round',
                mapMode: { type: 'cat' },
                pinnedRegionCodes: [],
                center: ALASKA_CENTER,
                zoom: ALASKA_ZOOM,
                scenario: { thresholds: BASELINE_THRESHOLDS, preset: null },
            },
        );

        expect(search).toBe('external=1');
    });

    it('keeps fractional zoom values stable in the URL', () => {
        const search = serializeMapUrlState('', {
            selectedRegionCode: null,
            season: 'year_round',
            mapMode: { type: 'cat' },
            pinnedRegionCodes: [],
            center: [63.31067, -158.42675],
            zoom: 4.54046159397577,
            scenario: { thresholds: BASELINE_THRESHOLDS, preset: null },
        });

        expect(new URLSearchParams(search).get('zoom')).toBe('4.54');
    });
});
