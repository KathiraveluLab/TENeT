import { useCallback, useRef, useState } from 'react';
import type L from 'leaflet';

export type SelectableMapMarker = L.Marker | L.CircleMarker;

export function useMapSelection(initialRegionCode: string | null) {
    const [selectedRegionCode, setSelectedRegionCode] = useState(initialRegionCode);
    const [detailsFocusKey, setDetailsFocusKey] = useState(0);
    const markerRefs = useRef<Record<string, SelectableMapMarker>>({});

    const registerMarker = useCallback((regionCode: string, marker: SelectableMapMarker | null) => {
        if (marker) markerRefs.current[regionCode] = marker;
        else delete markerRefs.current[regionCode];
    }, []);

    const selectRegion = useCallback((regionCode: string) => {
        setSelectedRegionCode(regionCode);
        setDetailsFocusKey(key => key + 1);
    }, []);

    const viewRegionDetails = useCallback((regionCode: string) => {
        setSelectedRegionCode(regionCode);
        setDetailsFocusKey(key => key + 1);
        markerRefs.current[regionCode]?.closePopup();
    }, []);

    return {
        selectedRegionCode,
        setSelectedRegionCode,
        detailsFocusKey,
        markerRefs,
        registerMarker,
        selectRegion,
        viewRegionDetails,
    };
}
