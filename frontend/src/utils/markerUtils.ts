/**
 * Shared Leaflet marker icon factory, used by RegionMarker and ScenarioLayer.
 */
import L from 'leaflet';

const markerIconCache = new Map<string, L.DivIcon>();

export function createMarkerIcon(color: string, selected = false): L.DivIcon {
    const cacheKey = `${color}:${selected ? 'selected' : 'default'}`;
    const cached = markerIconCache.get(cacheKey);
    if (cached) return cached;

    const size = selected ? 16 : 10;
    const anchor = size / 2;
    const icon = L.divIcon({
        className: 'custom-marker',
        html: `
            <div style="
                width: ${size}px;
                height: ${size}px;
                background-color: ${color};
                opacity: ${selected ? 1 : 0.8};
                border: ${selected ? 3 : 1.5}px solid rgba(255, 255, 255, 0.95);
                border-radius: 50%;
                box-shadow: 0 ${selected ? 2 : 1}px ${selected ? 8 : 3}px rgba(0,0,0,0.25);
            "></div>
        `,
        iconSize: [size, size],
        iconAnchor: [anchor, anchor],
        popupAnchor: [0, -anchor],
    });
    markerIconCache.set(cacheKey, icon);
    return icon;
}
