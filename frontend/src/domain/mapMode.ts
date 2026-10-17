export type BaseMapLayer = 'cat' | 'gap' | 'affordability';

export type MapMode =
    | { type: 'cat' }
    | { type: 'gapHunter' }
    | { type: 'telehealthAccess' }
    | { type: 'scenario' };

export const CAT_MAP_MODE: MapMode = { type: 'cat' };

export function mapModeFromLayer(layer: BaseMapLayer): MapMode {
    switch (layer) {
        case 'gap': return { type: 'gapHunter' };
        case 'affordability': return { type: 'telehealthAccess' };
        case 'cat': return CAT_MAP_MODE;
    }
}

export function baseLayerForMapMode(mode: MapMode): BaseMapLayer {
    switch (mode.type) {
        case 'gapHunter': return 'gap';
        case 'telehealthAccess': return 'affordability';
        case 'cat':
        case 'scenario':
            return 'cat';
    }
}
