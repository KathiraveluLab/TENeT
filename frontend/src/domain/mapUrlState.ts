import type { Season } from '../api/catApi';
import type { ScenarioThresholds } from '../types/scenario';
import type { MapMode } from './mapMode';

export const ALASKA_CENTER: [number, number] = [64.2, -152.0];
export const ALASKA_ZOOM = 4;
export const ALASKA_BOUNDS: [[number, number], [number, number]] = [
    [51.0, -188.0],
    [72.0, -129.0],
];

const STALE_DEFAULT_CENTERS: Array<[number, number]> = [
    [62.9752, -154.95117],
    [62.35, -146.75],
    [62.2, -141.8],
    [62.2, -170.8],
    [62.35, -136.5],
];

const OWNED_PARAMS = [
    'region', 'layer', 'season', 'pins', 'lat', 'lng', 'zoom',
    'scenario', 'bd', 'up', 'latency', 'aff', 'clinic', 'preset',
] as const;

export interface ParsedScenarioUrlState {
    thresholds: Partial<ScenarioThresholds>;
    preset: string | null;
}

export interface ParsedMapUrlState {
    selectedRegionCode: string | null;
    season: Season;
    mapMode: MapMode;
    pinnedRegionCodes: string[];
    center: [number, number];
    zoom: number;
    scenario: ParsedScenarioUrlState;
}

export interface SerializableMapUrlState {
    selectedRegionCode: string | null;
    season: Season;
    mapMode: MapMode;
    pinnedRegionCodes: string[];
    center: [number, number];
    zoom: number;
    scenario: {
        thresholds: ScenarioThresholds;
        preset: string | null;
    };
}

function validNumber(value: string | null): number | null {
    if (value === null || value.trim() === '') return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
}

function parseScenarioParams(params: URLSearchParams): ParsedScenarioUrlState {
    if (params.get('scenario') !== '1') return { thresholds: {}, preset: null };

    const thresholds: Partial<ScenarioThresholds> = {};
    const download = validNumber(params.get('bd'));
    const upload = validNumber(params.get('up'));
    const affordability = validNumber(params.get('aff'));
    const latencyParam = params.get('latency');
    const clinicParam = params.get('clinic');

    if (download !== null) thresholds.min_download_mbps = download;
    if (upload !== null) thresholds.min_upload_mbps = upload;
    if (affordability !== null) thresholds.affordability_burden_pct = affordability;
    if (latencyParam === 'baseline') thresholds.max_latency_ms = null;
    else {
        const latency = validNumber(latencyParam);
        if (latency !== null) thresholds.max_latency_ms = latency;
    }
    if (clinicParam === 'baseline') thresholds.clinic_proximity_km = null;
    else {
        const clinic = validNumber(clinicParam);
        if (clinic !== null) thresholds.clinic_proximity_km = clinic;
    }

    return { thresholds, preset: params.get('preset') };
}

export function parseMapUrlState(search: string): ParsedMapUrlState {
    const params = new URLSearchParams(search);
    const seasonParam = params.get('season');
    const layerParam = params.get('layer');
    const lat = validNumber(params.get('lat'));
    const lng = validNumber(params.get('lng'));
    const zoom = validNumber(params.get('zoom'));
    const hasSafeCenter = lat !== null && lng !== null
        && lat >= ALASKA_BOUNDS[0][0] && lat <= ALASKA_BOUNDS[1][0]
        && lng >= ALASKA_BOUNDS[0][1] && lng <= ALASKA_BOUNDS[1][1];
    const hasSafeZoom = zoom !== null && zoom >= 4 && zoom <= 18;
    const hasStaleDefaultViewport = hasSafeCenter && hasSafeZoom
        && STALE_DEFAULT_CENTERS.some(([staleLat, staleLng]) => (
            Math.abs(lat - staleLat) < 0.0001 && Math.abs(lng - staleLng) < 0.0001
        ))
        && zoom === ALASKA_ZOOM;

    let mapMode: MapMode = { type: 'cat' };
    if (params.get('scenario') === '1') mapMode = { type: 'scenario' };
    else if (layerParam === 'gap') mapMode = { type: 'gapHunter' };
    else if (layerParam === 'affordability') mapMode = { type: 'telehealthAccess' };

    return {
        selectedRegionCode: params.get('region'),
        season: seasonParam === 'summer' || seasonParam === 'winter' || seasonParam === 'year_round'
            ? seasonParam
            : 'year_round',
        mapMode,
        pinnedRegionCodes: (params.get('pins') ?? '')
            .split(',')
            .map(code => code.trim())
            .filter(Boolean)
            .slice(0, 3),
        center: hasSafeCenter && !hasStaleDefaultViewport ? [lat, lng] : ALASKA_CENTER,
        zoom: hasSafeZoom && !hasStaleDefaultViewport ? zoom : ALASKA_ZOOM,
        scenario: parseScenarioParams(params),
    };
}

export function serializeMapUrlState(
    currentSearch: string,
    state: SerializableMapUrlState,
): string {
    const params = new URLSearchParams(currentSearch);
    OWNED_PARAMS.forEach(param => params.delete(param));

    if (state.selectedRegionCode) params.set('region', state.selectedRegionCode);
    if (state.mapMode.type === 'gapHunter') params.set('layer', 'gap');
    if (state.mapMode.type === 'telehealthAccess') params.set('layer', 'affordability');
    if (state.season !== 'year_round') params.set('season', state.season);
    if (state.pinnedRegionCodes.length) params.set('pins', state.pinnedRegionCodes.slice(0, 3).join(','));
    if (state.center[0] !== ALASKA_CENTER[0]) params.set('lat', state.center[0].toFixed(5));
    if (state.center[1] !== ALASKA_CENTER[1]) params.set('lng', state.center[1].toFixed(5));
    if (state.zoom !== ALASKA_ZOOM) params.set('zoom', String(state.zoom));

    if (state.mapMode.type === 'scenario') {
        const { thresholds, preset } = state.scenario;
        params.set('scenario', '1');
        params.set('bd', String(thresholds.min_download_mbps));
        params.set('up', String(thresholds.min_upload_mbps));
        params.set('latency', thresholds.max_latency_ms === null
            ? 'baseline'
            : String(thresholds.max_latency_ms));
        params.set('aff', String(thresholds.affordability_burden_pct));
        params.set('clinic', thresholds.clinic_proximity_km === null
            ? 'baseline'
            : String(thresholds.clinic_proximity_km));
        if (preset) params.set('preset', preset);
    }

    return params.toString();
}
