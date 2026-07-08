import L from 'leaflet';

const markerIconCache = new Map<string, L.DivIcon>();

export function createMarkerIcon(color: string, selected = false, size = 24, text?: string): L.DivIcon {
    const cacheKey = `${color}:${selected}:${size}:${text || ''}`;
    const cached = markerIconCache.get(cacheKey);
    if (cached) return cached;

    const actualSize = selected ? size * 1.3 : size;
    const diagonal = Math.ceil(actualSize * Math.SQRT2);
    const anchor = diagonal / 2;
    const innerSize = selected ? actualSize * 0.4 : actualSize * 0.35;

    const html = `
    <div style="width: ${diagonal}px; height: ${diagonal}px; display: flex; align-items: center; justify-content: center; position: relative;">
      <div style="
        width: ${actualSize}px;
        height: ${actualSize}px;
        background: white;
        border: ${selected ? '2px solid #475569' : '1.5px solid #cbd5e1'};
        border-radius: 50% 50% 0 50%;
        transform: rotate(45deg);
        box-shadow: ${selected ? '2px 2px 4px rgba(0,0,0,0.3)' : '1px 1px 2px rgba(0,0,0,0.15)'};
        display: flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
      " class="healthsites-cluster-wrapper">
        <div style="
          transform: rotate(-45deg);
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          height: 100%;
          position: relative;
        ">
          <div style="
            width: ${innerSize}px;
            height: ${innerSize}px;
            border-radius: 50%;
            background-color: ${color};
            ${selected ? 'box-shadow: 0 0 0 2px white;' : ''}
          "></div>
          ${text ? `<div style="position: absolute; font-size: ${Math.round(actualSize * 0.45)}px; font-weight: 800; color: #1e293b; top: -14px;">${text}</div>` : ''}
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
