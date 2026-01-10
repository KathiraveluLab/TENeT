import React, { useState, useEffect } from 'react';
import { CircleMarker, Popup, useMap } from 'react-leaflet';
import {
    RegionTelehealthStatus,
    AllTelehealthStatusResponse,
    fetchAllTelehealthStatus
} from '../api/catApi';

interface AffordabilityLayerProps {
    visible: boolean;
    onDataLoad?: (summary: AllTelehealthStatusResponse['summary']) => void;
}

/**
 * Affordability Layer - shows all regions colored by telehealth accessibility status
 * Green = Telehealth Ready (affordable home internet)
 * Amber = Community Anchor (unaffordable but has nearby clinic)
 * Red = Critical Gap (unaffordable AND no nearby clinic)
 * Gray = Data Unavailable
 */
export default function AffordabilityLayer({ visible, onDataLoad }: AffordabilityLayerProps) {
    const [data, setData] = useState<AllTelehealthStatusResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const map = useMap();

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
                    key={region.region_code}
                    center={[region.lat, region.lon]}
                    radius={8}
                    pathOptions={{
                        fillColor: region.color,
                        fillOpacity: 0.8,
                        color: 'white',
                        weight: 2
                    }}
                >
                    <Popup>
                        <div style={{ minWidth: '260px' }}>
                            <h4 style={{ margin: '0 0 8px 0', color: '#1e40af', fontSize: '16px' }}>
                                {region.region_name}
                            </h4>

                            <div style={{
                                display: 'inline-block',
                                padding: '4px 12px',
                                borderRadius: '12px',
                                backgroundColor: region.color,
                                color: 'white',
                                fontSize: '12px',
                                fontWeight: '600',
                                marginBottom: '12px'
                            }}>
                                {region.status.replace(/_/g, ' ')}
                            </div>

                            {/* Affordability Section */}
                            <div style={{
                                backgroundColor: '#f8fafc',
                                border: '1px solid #e2e8f0',
                                borderRadius: '6px',
                                padding: '10px',
                                marginBottom: '10px',
                                fontSize: '12px'
                            }}>
                                <div style={{ fontWeight: '600', color: '#475569', marginBottom: '6px' }}>
                                    Affordability
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', color: '#374151' }}>
                                    <span>Internet:</span>
                                    <strong>${region.internet_cost}/mo ({(region as any).isp_name || 'N/A'})</strong>

                                    {(region as any).median_income && (
                                        <>
                                            <span>Median Income:</span>
                                            <strong>${((region as any).median_income).toLocaleString()}/yr</strong>
                                        </>
                                    )}

                                    <span>Burden:</span>
                                    <strong style={{ color: region.burden_pct && region.burden_pct < 2 ? '#16a34a' : '#dc2626' }}>
                                        {region.burden_pct ? `${region.burden_pct}%` : 'N/A'}
                                        {region.burden_pct && (region.burden_pct < 2 ? ' ✓' : ' (>2%)')}
                                    </strong>
                                </div>
                            </div>

                            {/* Healthcare Section */}
                            <div style={{
                                backgroundColor: '#f8fafc',
                                border: '1px solid #e2e8f0',
                                borderRadius: '6px',
                                padding: '10px',
                                marginBottom: '10px',
                                fontSize: '12px'
                            }}>
                                <div style={{ fontWeight: '600', color: '#475569', marginBottom: '6px' }}>
                                    Healthcare Safety Net
                                </div>
                                <div style={{ color: '#374151' }}>
                                    {(region as any).nearest_clinic_name ? (
                                        <div>
                                            <strong>Nearest:</strong> {(region as any).nearest_clinic_name.substring(0, 30)}
                                            {(region as any).nearest_clinic_name.length > 30 ? '...' : ''}
                                            ({(region as any).nearest_clinic_km}km)
                                        </div>
                                    ) : (
                                        <div style={{ color: '#dc2626' }}>No clinic data available</div>
                                    )}
                                    <div style={{ marginTop: '4px' }}>
                                        <strong>Access:</strong> {(region as any).access_mode || 'Unknown'}
                                    </div>
                                </div>
                            </div>

                            {/* Recommendation */}
                            <div style={{
                                backgroundColor: region.status === 'CRITICAL_GAP' ? '#fef2f2' :
                                    region.status === 'TELEHEALTH_READY' ? '#f0fdf4' : '#fffbeb',
                                border: `1px solid ${region.status === 'CRITICAL_GAP' ? '#fecaca' :
                                    region.status === 'TELEHEALTH_READY' ? '#86efac' : '#fde68a'}`,
                                borderRadius: '6px',
                                padding: '10px',
                                fontSize: '11px'
                            }}>
                                <div style={{ fontWeight: '600', color: '#475569', marginBottom: '4px' }}>
                                    Recommendation
                                </div>
                                <div style={{ color: '#374151' }}>
                                    {(region as any).recommendation || 'No recommendation available'}
                                </div>
                            </div>
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
    return (
        <div style={{
            position: 'absolute',
            bottom: '20px',
            left: '20px',
            backgroundColor: 'white',
            padding: '12px',
            borderRadius: '8px',
            boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
            zIndex: 1000,
            fontSize: '12px'
        }}>
            <div style={{ fontWeight: '600', marginBottom: '8px' }}>Telehealth Accessibility</div>

            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
                <div style={{ width: '14px', height: '14px', borderRadius: '50%', backgroundColor: '#22c55e', marginRight: '8px' }} />
                <span>Telehealth Ready {summary && `(${summary.telehealth_ready})`}</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
                <div style={{ width: '14px', height: '14px', borderRadius: '50%', backgroundColor: '#f59e0b', marginRight: '8px' }} />
                <span>Community Anchor {summary && `(${summary.community_anchor})`}</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
                <div style={{ width: '14px', height: '14px', borderRadius: '50%', backgroundColor: '#ef4444', marginRight: '8px' }} />
                <span>Critical Gap {summary && `(${summary.critical_gap})`}</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ width: '14px', height: '14px', borderRadius: '50%', backgroundColor: '#6b7280', marginRight: '8px' }} />
                <span>Data Unavailable {summary && `(${summary.data_unavailable})`}</span>
            </div>
        </div>
    );
}
