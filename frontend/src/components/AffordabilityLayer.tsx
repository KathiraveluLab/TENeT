import React, { useCallback, useEffect, useRef, useState } from 'react';
import { CircleMarker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import {
    AllTelehealthStatusResponse,
    fetchAllTelehealthStatus
} from '../api/catApi';

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
 * Affordability Layer - shows all regions colored by telehealth accessibility status
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
        if (visible && !data) {
            setLoading(true);
            fetchAllTelehealthStatus()
                .then(response => {
                    setData(response);
                    if (onDataLoad) {
                        onDataLoad(response.summary);
                    }
                })
                .catch(err => setError(err.message))
                .finally(() => setLoading(false));
        }
    }, [visible, data, onDataLoad]);

    if (!visible) return null;
    if (loading) return null;  // Could add a loading spinner
    if (error) {
        console.error('AffordabilityLayer error:', error);
        return null;
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
                        fillColor: region.color,
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
                        <div style={{
                            minWidth: '210px',
                            maxWidth: '236px',
                            color: '#172033',
                            fontSize: '12px'
                        }}>
                            <h4 style={{
                                margin: '0 0 2px 0',
                                color: '#111827',
                                fontSize: '15px',
                                lineHeight: 1.2
                            }}>
                                {region.region_name}
                            </h4>
                            <div style={{
                                marginBottom: '9px',
                                color: '#64748b',
                                fontSize: '11px',
                                fontWeight: 700
                            }}>
                                {region.region_code}
                            </div>

                            <div style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                minHeight: '22px',
                                padding: '3px 8px',
                                borderRadius: '999px',
                                backgroundColor: region.color,
                                color: 'white',
                                fontSize: '11px',
                                fontWeight: 800,
                                marginBottom: '10px'
                            }}>
                                {region.status.replace(/_/g, ' ')}
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
                                        markerRefs.current[region.region_code]?.closePopup();
                                    }
                                }}
                                style={{
                                    width: '100%',
                                    border: '1px solid #c7d0da',
                                    borderRadius: '6px',
                                    background: '#ffffff',
                                    color: '#334155',
                                    padding: '6px 8px',
                                    fontSize: '11px',
                                    fontWeight: 800,
                                    cursor: 'pointer'
                                }}
                            >
                                View details
                            </button>
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
    const items = [
        { color: '#10B981', label: 'Telehealth Ready', sub: 'Affordable + Fast', count: summary?.telehealth_ready },
        { color: '#F59E0B', label: 'Community Anchor', sub: 'Has nearby clinic', count: summary?.community_anchor },
        { color: '#EF4444', label: 'Critical Gap', sub: 'No affordable access', count: summary?.critical_gap },
        { color: '#94A3B8', label: 'Data Unavailable', sub: 'Missing data', count: summary?.data_unavailable },
    ];

    return (
        <div style={{
            position: 'absolute',
            bottom: '20px',
            left: '20px',
            zIndex: 1000,
            minWidth: '220px',
            // Glassmorphism
            background: 'rgba(255, 255, 255, 0.92)',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            padding: '16px 18px',
            borderRadius: '12px',
            border: '1px solid rgba(255, 255, 255, 0.3)',
            boxShadow: '0 8px 32px rgba(31, 38, 135, 0.12)',
            fontSize: '12px'
        }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '12px',
                paddingBottom: '10px',
                borderBottom: '1px solid rgba(0, 0, 0, 0.08)'
            }}>
                <div style={{ fontWeight: '700', color: '#0f172a', fontSize: '14px', letterSpacing: '-0.02em' }}>
                    Telehealth Accessibility
                </div>
                <span style={{ fontSize: '10px', color: '#64748b', fontWeight: '500' }}>Safety Net</span>
            </div>

            {items.map(item => (
                <div key={item.label} style={{ display: 'flex', alignItems: 'flex-start', marginBottom: '8px', gap: '10px' }}>
                    <div style={{
                        width: '12px',
                        height: '12px',
                        borderRadius: '50%',
                        backgroundColor: item.color,
                        flexShrink: 0,
                        marginTop: '3px',
                        boxShadow: '0 1px 2px rgba(0,0,0,0.15)'
                    }} />
                    <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ color: '#1e293b', fontWeight: '500' }}>{item.label}</span>
                            {item.count !== undefined && (
                                <span style={{ fontSize: '10px', color: '#64748b', fontWeight: '600' }}>{item.count}</span>
                            )}
                        </div>
                        <div style={{ color: '#64748b', fontSize: '10px' }}>{item.sub}</div>
                    </div>
                </div>
            ))}
        </div>
    );
}
