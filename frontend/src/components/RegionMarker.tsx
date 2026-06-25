import { useCallback, useRef } from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import {
    CATRegion,
    getNeedColor,
    getNeedLabel,
    getTierColor,
} from '../api/catApi';
import { createMarkerIcon } from '../utils/markerUtils';

interface RegionMarkerProps {
    region: CATRegion;
    selected?: boolean;
    onSelect?: (regionCode: string) => void;
    onViewDetails?: (regionCode: string) => void;
    onMarkerReady?: (regionCode: string, marker: L.Marker | null) => void;
}

function badgeStyle(backgroundColor: string) {
    return {
        display: 'inline-flex',
        alignItems: 'center',
        minHeight: 22,
        padding: '3px 8px',
        borderRadius: 999,
        backgroundColor,
        color: '#ffffff',
        fontSize: 11,
        fontWeight: 800,
        lineHeight: 1.2,
        whiteSpace: 'nowrap' as const,
    };
}

export default function RegionMarker({
    region,
    selected = false,
    onSelect,
    onViewDetails,
    onMarkerReady,
}: RegionMarkerProps) {
    const markerRef = useRef<L.Marker | null>(null);

    const markerRefCallback = useCallback((marker: L.Marker | null) => {
        markerRef.current = marker;
        onMarkerReady?.(region.region_code, marker);
    }, [onMarkerReady, region.region_code]);

    if (region.centroid_lat === null || region.centroid_lon === null) {
        return null;
    }

    const needColor = getNeedColor(region.necessity_score);
    const needLabel = getNeedLabel(region.necessity_score);
    const tierColor = getTierColor(region.tier_level);

    return (
        <Marker
            ref={markerRefCallback}
            position={[region.centroid_lat, region.centroid_lon]}
            icon={createMarkerIcon(needColor, selected)}
            eventHandlers={{
                click: () => onSelect?.(region.region_code),
            }}
        >
            <Popup
                autoPan
                keepInView
                maxWidth={260}
                minWidth={220}
                autoPanPaddingTopLeft={[64, 120]}
                autoPanPaddingBottomRight={[64, 210]}
            >
                <div style={{
                    minWidth: 210,
                    maxWidth: 236,
                    color: '#172033',
                    fontSize: 12,
                }}>
                    <h3 style={{
                        margin: '0 0 2px',
                        color: '#111827',
                        fontSize: 15,
                        lineHeight: 1.2,
                        fontWeight: 800,
                    }}>
                        {region.region_name}
                    </h3>
                    <div style={{
                        marginBottom: 9,
                        color: '#64748b',
                        fontSize: 11,
                        fontWeight: 700,
                    }}>
                        {region.region_code}
                    </div>

                    <div style={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: 6,
                        marginBottom: 10,
                    }}>
                        <span style={badgeStyle(tierColor)}>CAT {region.tier_level}</span>
                        <span style={badgeStyle(needColor)}>{needLabel}</span>
                    </div>

                    <button
                        type="button"
                        onMouseDown={event => {
                            event.preventDefault();
                            event.stopPropagation();
                        }}
                        onClick={event => {
                            event.preventDefault();
                            event.stopPropagation();
                            if (onViewDetails) {
                                onViewDetails(region.region_code);
                            } else {
                                onSelect?.(region.region_code);
                                markerRef.current?.closePopup();
                            }
                        }}
                        style={{
                            width: '100%',
                            border: '1px solid #c7d0da',
                            borderRadius: 6,
                            background: '#ffffff',
                            color: '#334155',
                            padding: '6px 8px',
                            fontSize: 11,
                            fontWeight: 800,
                            cursor: 'pointer',
                        }}
                    >
                        View details
                    </button>
                </div>
            </Popup>
        </Marker>
    );
}
