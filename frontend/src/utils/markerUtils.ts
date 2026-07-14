import L from 'leaflet';
import type { ScenarioTelehealthStatusName } from '../domain/statusPresentation';
import { escapeHtml } from './escapeHtml';

const markerIconCache = new Map<string, L.DivIcon>();

export interface MarkerMetadata {
    needScore?: number;
    scenarioStatus?: ScenarioTelehealthStatusName;
}

export interface MarkerClusterLike {
    getChildCount: () => number;
    getAllChildMarkers: () => L.Marker[];
}

type MarkerWithMetadata = L.Marker & {
    options: L.MarkerOptions & MarkerMetadata;
};

export function setMarkerMetadata(marker: L.Marker, metadata: MarkerMetadata): void {
    Object.assign((marker as MarkerWithMetadata).options, metadata);
}

export function getMarkerMetadata(marker: L.Marker): Readonly<MarkerMetadata> {
    return (marker as MarkerWithMetadata).options;
}

export function getClusterMarkerSize(pointCount: number): number {
    if (pointCount >= 200) return 36;
    if (pointCount >= 50) return 32.4;
    if (pointCount >= 10) return 28.8;
    return 24;
}

function safeMarkerColor(color: string): string {
    return /^#[0-9a-f]{3,8}$/i.test(color) ? color : '#94a3b8';
}

/**
 * Shared Leaflet marker icon factory.
 *
 * Reverting to the exact architecture of the original dots as requested:
 * simple circular dots centered precisely on the coordinate.
 * Clusters will just be slightly larger dots with the number centered inside.
 */
export function createMarkerIcon(color: string, selected = false, size = 24, text?: string): L.DivIcon {
    const markerColor = safeMarkerColor(color);
    const cacheKey = `${markerColor}:${selected}:${size}:${text || ''}`;
    const cached = markerIconCache.get(cacheKey);
    if (cached) return cached;

    const actualSize = selected ? size * 1.3 : size;
    const diagonal = Math.ceil(actualSize * Math.SQRT2);
    const anchor = diagonal / 2;
    const innerSize = selected ? actualSize * 0.4 : actualSize * 0.35;

    const html = `
    <div class="tenet-marker-shell" style="--marker-shell-size:${diagonal}px;--marker-size:${actualSize}px;--marker-dot-size:${innerSize}px;--marker-color:${markerColor};--marker-count-size:${Math.round(actualSize * 0.45)}px">
      <div class="tenet-marker-pin${selected ? ' is-selected' : ''}">
        <div class="tenet-marker-content">
          <div class="tenet-marker-dot"></div>
          ${text ? `<div class="tenet-marker-count">${escapeHtml(text)}</div>` : ''}
        </div>
      </div>
    </div>
    `;

    const icon = L.divIcon({
        className: 'custom-css-marker',
        html,
        iconSize: [diagonal, diagonal],
        iconAnchor: [anchor, diagonal],
        popupAnchor: [0, -diagonal + (actualSize * 0.2)],
    });

    markerIconCache.set(cacheKey, icon);
    return icon;
}
