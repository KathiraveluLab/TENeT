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
                    radius={4}
                    pathOptions={{
                        fillColor: region.color,
                        fillOpacity: 0.65,    // Gemstone effect
                        color: '#ffffff',
                        weight: 1.5,          // Thicker stroke
                        opacity: 0.9
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
                                    <strong>${region.internet_cost}/mo ({region.isp_name || 'N/A'})</strong>

                                    {region.median_income && (
                                        <>
                                            <span>Median Income:</span>
                                            <strong>${(region.median_income).toLocaleString()}/yr</strong>
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
                                    {region.nearest_clinic_name ? (
                                        <div>
                                            <strong>Nearest:</strong> {region.nearest_clinic_name.substring(0, 30)}
                                            {region.nearest_clinic_name.length > 30 ? '...' : ''}
                                            ({region.nearest_clinic_km}km)
                                        </div>
                                    ) : (
                                        <div style={{ color: '#dc2626' }}>No clinic data available</div>
                                    )}
                                    <div style={{ marginTop: '4px' }}>
                                        <strong>Access:</strong> {region.access_mode || 'Unknown'}
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
                                    {region.recommendation || 'No recommendation available'}
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

