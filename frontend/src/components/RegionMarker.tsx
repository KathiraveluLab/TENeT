import { useCallback, useRef, useMemo } from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import {
    CATRegion,
    Season
} from '../api/catApi';
import { CAT_TIER_PRESENTATION, getDesertScorePresentation } from '../domain/metrics';
import { createMarkerIcon, setMarkerMetadata } from '../utils/markerUtils';
import Button from './ui/Button';
import StatusBadge from './ui/StatusBadge';
import './map/MapLayers.css';

interface RegionMarkerProps {
    region: CATRegion;
    selected?: boolean;
    onSelect?: (regionCode: string) => void;
    onViewDetails?: (regionCode: string) => void;
    onMarkerReady?: (regionCode: string, marker: L.Marker | null) => void;
    activeSeason?: Season;
    onClick?: () => void;
    needScore?: number;
}

export default function RegionMarker({
    region,
    selected = false,
    onSelect,
    onViewDetails,
    onMarkerReady,
    onClick,
    needScore
}: RegionMarkerProps) {
    const markerRef = useRef<L.Marker | null>(null);

    const markerRefCallback = useCallback((marker: L.Marker | null) => {
        markerRef.current = marker;
        if (marker) {
            // Attach score directly to leaflet marker options so the clustering
            // algorithm in RegionClusters can read it to calculate average color
            const score = needScore ?? region.necessity_score;
            setMarkerMetadata(marker, { needScore: Number.isFinite(score) ? score : undefined });
        }
        onMarkerReady?.(region.region_code, marker);
    }, [onMarkerReady, region.region_code, needScore, region.necessity_score]);

    if (region.centroid_lat === null || region.centroid_lon === null) {
        return null;
    }

    const needPresentation = Number.isFinite(region.necessity_score)
        ? getDesertScorePresentation(region.necessity_score)
        : null;
    const markerIcon = useMemo(
        () => createMarkerIcon(needPresentation?.color ?? '#94a3b8', selected),
        [needPresentation?.color, selected],
    );

    return (
        <Marker
            ref={markerRefCallback}
            position={[region.centroid_lat, region.centroid_lon]}
            icon={markerIcon}
            alt={`${region.region_name} community marker`}
            title={region.region_name}
            eventHandlers={{
                click: () => {
                    onSelect?.(region.region_code);
                    onClick?.();
                }
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
                <div className="region-marker-popup">
                    <h3 className="region-marker-popup__title">
                        {region.region_name}
                    </h3>
                    <div className="region-marker-popup__code">
                        {region.region_code}
                    </div>

                    <div className="region-marker-popup__badges">
                        <StatusBadge tone={CAT_TIER_PRESENTATION[region.tier_level].tone}>CAT {region.tier_level}</StatusBadge>
                        <StatusBadge tone={needPresentation?.tone ?? 'neutral'}>
                            {needPresentation?.label ?? 'Data unavailable'}
                        </StatusBadge>
                    </div>

                    <Button
                        size="small"
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
                        className="region-marker-popup__button"
                    >
                        View details
                    </Button>
                </div>
            </Popup>
        </Marker>
    );
}
