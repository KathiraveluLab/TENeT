import { useCallback, useEffect, useRef, useState } from 'react';
import { CircleMarker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import {
    AllTelehealthStatusResponse,
    fetchAllTelehealthStatus
} from '../api/catApi';
import { errorMessage, isAbortError } from '../api/http';
import Button from './ui/Button';
import StatusBadge from './ui/StatusBadge';
import {
    BASE_TELEHEALTH_STATUSES,
    getTelehealthStatusColor,
    getTelehealthStatusLabel,
    getTelehealthStatusPresentation,
    getTelehealthStatusTone,
} from '../domain/statusPresentation';
import './MapModeLegends.css';
import './map/MapLayers.css';

interface AffordabilityLayerProps {
    visible: boolean;
    selectedRegionCode?: string | null;
    onSelect?: (regionCode: string) => void;
    onViewDetails?: (regionCode: string) => void;
    onMarkerReady?: (regionCode: string, marker: L.CircleMarker | null) => void;
    onDataLoad?: (summary: AllTelehealthStatusResponse['summary']) => void;
}

const AFFORDABILITY_MARKER_PANE = 'affordability-marker-pane';

/**
 * Affordability layer - shows all regions colored by composite access status.
 * Green = Telehealth Ready (affordable home internet)
 * Amber = Community Anchor (unaffordable but has nearby clinic)
 * Red = Critical Gap (unaffordable AND no nearby clinic)
 * Gray = Data Unavailable
 */
export default function AffordabilityLayer({
    visible,
    selectedRegionCode,
    onSelect,
    onViewDetails,
    onMarkerReady,
    onDataLoad
}: AffordabilityLayerProps) {
    const [data, setData] = useState<AllTelehealthStatusResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const map = useMap();
    const markerRefs = useRef<Record<string, L.CircleMarker>>({});

    useEffect(() => {
        const pane = map.getPane(AFFORDABILITY_MARKER_PANE) ?? map.createPane(AFFORDABILITY_MARKER_PANE);
        pane.style.zIndex = '650';
        pane.style.pointerEvents = 'auto';
    }, [map]);

    const registerAffordabilityMarker = useCallback((regionCode: string, marker: L.CircleMarker | null) => {
        if (marker) {
            markerRefs.current[regionCode] = marker;
        } else {
            delete markerRefs.current[regionCode];
        }
        onMarkerReady?.(regionCode, marker);
    }, [onMarkerReady]);

    useEffect(() => {
        if (!visible || !selectedRegionCode) return;

        const marker = markerRefs.current[selectedRegionCode];
        if (!marker) return;

        window.setTimeout(() => {
            marker.openPopup();
        }, 380);
    }, [data, selectedRegionCode, visible]);

    useEffect(() => {
        if (!visible || data) return;

        const controller = new AbortController();
        setLoading(true);
        fetchAllTelehealthStatus(controller.signal)
            .then(response => {
                setData(response);
                onDataLoad?.(response.summary);
            })
            .catch((caught: unknown) => {
                if (!isAbortError(caught)) {
                    setError(errorMessage(caught, 'Affordability layer unavailable'));
                }
            })
            .finally(() => {
                if (!controller.signal.aborted) setLoading(false);
            });

        return () => controller.abort();
    }, [visible, data, onDataLoad]);

    if (!visible) return null;
    if (loading) return null;
    if (error) {
        return <div className="map-layer-state is-error" role="status">{error}</div>;
    }
    if (!data) return null;

    return (
        <>
            {data.regions.map((region) => (
                <CircleMarker
                    ref={(marker) => registerAffordabilityMarker(region.region_code, marker)}
                    key={region.region_code}
                    center={[region.lat, region.lon]}
                    radius={region.region_code === selectedRegionCode ? 6 : 4}
                    pane={AFFORDABILITY_MARKER_PANE}
                    interactive
                    bubblingMouseEvents={false}
                    pathOptions={{
                        fillColor: getTelehealthStatusColor(region.status),
                        fillOpacity: region.region_code === selectedRegionCode ? 0.95 : 0.65,
                        color: '#ffffff',
                        weight: region.region_code === selectedRegionCode ? 2.5 : 1.5,
                        opacity: 0.9
                    }}
                    eventHandlers={{
                        click: (event) => {
                            event.originalEvent?.stopPropagation();
                            onSelect?.(region.region_code);
                            event.target.openPopup();
                        },
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
                        <div className="telehealth-access-popup">
                            <h4 className="telehealth-access-popup__title">
                                {region.region_name}
                            </h4>
                            <div className="telehealth-access-popup__code">
                                {region.region_code}
                            </div>

                            <StatusBadge
                                tone={getTelehealthStatusTone(region.status)}
                                className="telehealth-access-popup__status"
                            >
                                {getTelehealthStatusLabel(region.status)}
                            </StatusBadge>

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
                                        markerRefs.current[region.region_code]?.closePopup();
                                    }
                                }}
                                className="telehealth-access-popup__button"
                            >
                                View details
                            </Button>
                        </div>
                    </Popup>
                </CircleMarker>
            ))}
        </>
    );
}

/**
 * Legend component for the affordability layer
 */
export function AffordabilityLegend({ summary }: { summary?: AllTelehealthStatusResponse['summary'] }) {
    const counts = {
        TELEHEALTH_READY: summary?.telehealth_ready,
        COMMUNITY_ANCHOR: summary?.community_anchor,
        CRITICAL_GAP: summary?.critical_gap,
        DATA_UNAVAILABLE: summary?.data_unavailable,
    } as const;
    const items = BASE_TELEHEALTH_STATUSES.map(status => ({
        ...getTelehealthStatusPresentation(status),
        sub: getTelehealthStatusPresentation(status).description,
        count: counts[status],
    }));

    return (
        <div className="affordability-legend">
            <div className="affordability-legend__header">
                <div className="affordability-legend__title">
                    Affordability
                </div>
                <span className="affordability-legend__kicker">Safety Net</span>
            </div>

            {items.map(item => (
                <div key={item.label} className="affordability-legend__item">
                    <div
                        className="affordability-legend__swatch"
                        style={{ backgroundColor: item.color }}
                    />
                    <div className="affordability-legend__content">
                        <div className="affordability-legend__row">
                            <span className="affordability-legend__label">{item.label}</span>
                            {item.count !== undefined && (
                                <span className="affordability-legend__count">{item.count}</span>
                            )}
                        </div>
                        <div className="affordability-legend__note">{item.sub}</div>
                    </div>
                </div>
            ))}
        </div>
    );
}
