import { useEffect } from 'react';
import { useMap, useMapEvents } from 'react-leaflet';
import type { RegionSummary } from '../../api/catApi';
import type { SelectableMapMarker } from '../../hooks/useMapSelection';

interface MapViewportControllerProps {
    center: [number, number];
    zoom: number;
    onViewportChange: (center: [number, number], zoom: number) => void;
}

export function MapViewportController({
    center,
    zoom,
    onViewportChange,
}: MapViewportControllerProps) {
    const map = useMapEvents({
        moveend: () => {
            const nextZoom = map.getZoom();

            // Continuous wheel zoom deliberately ends at a fractional level.
            // Keep that interaction local to Leaflet so it cannot trigger an
            // App render and URL rewrite at the end of every gesture.
            if (!Number.isInteger(nextZoom)) return;

            const nextCenter = map.getCenter();
            onViewportChange(
                [Number(nextCenter.lat.toFixed(5)), Number(nextCenter.lng.toFixed(5))],
                nextZoom,
            );
        },
    });

    useEffect(() => {
        const current = map.getCenter();
        if (
            Math.abs(current.lat - center[0]) < 0.00001
            && Math.abs(current.lng - center[1]) < 0.00001
            && Math.abs(map.getZoom() - zoom) < 0.0005
        ) return;
        map.setView(center, zoom, { animate: false });
    }, [center, map, zoom]);

    return null;
}

export function ComparisonMapController({ active }: { active: boolean }) {
    const map = useMap();

    useEffect(() => {
        if (!active) return;
        map.closePopup();
        map.panBy([0, 96], { animate: true, duration: 0.25 });
    }, [active, map]);

    return null;
}

interface SelectionControllerProps {
    selectedRegionCode: string | null;
    regionSummaries: RegionSummary[];
    markerRefs: React.MutableRefObject<Record<string, SelectableMapMarker>>;
}

export function SelectionController({
    selectedRegionCode,
    regionSummaries,
    markerRefs,
}: SelectionControllerProps) {
    const map = useMap();

    useEffect(() => {
        if (!selectedRegionCode) return;
        const selected = regionSummaries.find(region => region.region_code === selectedRegionCode);
        if (!selected || selected.lat === null || selected.lon === null) return;

        map.flyTo([selected.lat, selected.lon], Math.max(map.getZoom(), 8), { duration: 1.1 });
        const timer = window.setTimeout(() => {
            markerRefs.current[selectedRegionCode]?.openPopup();
        }, 350);
        return () => window.clearTimeout(timer);
    }, [map, markerRefs, regionSummaries, selectedRegionCode]);

    return null;
}
