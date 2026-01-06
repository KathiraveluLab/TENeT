import React, { useEffect, useState, useMemo } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import {
    AffordabilityZone,
    AffordabilityResponse,
    fetchAffordability
} from '../api/catApi';

interface AffordabilityLayerProps {
    visible: boolean;
    onToggle: () => void;
    onModeChange?: (isActive: boolean) => void;
}

/**
 * Digital Equity Layer - Shows internet affordability by ZCTA
 * 
 * Reveals the "Affordability Gap" - areas where internet may be available
 * but is economically inaccessible (cost > 2% of monthly income).
 * 
 * Uses regional ISP pricing:
 * - GCI (cities): $125/mo
 * - FastWyre (rural): $350/mo
 * - Extreme Rural (remote): $450/mo
 */
export default function AffordabilityLayer({ visible, onToggle, onModeChange }: AffordabilityLayerProps) {
    const [data, setData] = useState<AffordabilityResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const layerRef = React.useRef<L.LayerGroup | null>(null);
    const map = useMap();

    // Notify parent of mode changes
    useEffect(() => {
        if (onModeChange) {
            onModeChange(visible);
        }
    }, [visible, onModeChange]);

    // Load data when visible
    useEffect(() => {
        if (visible && !data) {
            loadData();
        }
        if (!visible && layerRef.current) {
            layerRef.current.clearLayers();
        }
    }, [visible]);

    // Render markers when data changes
    useEffect(() => {
        if (visible && data) {
            renderMarkers(data.zones);
        }
    }, [visible, data]);

    async function loadData() {
        try {
            setLoading(true);
            setError(null);
            const response = await fetchAffordability();
            setData(response);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to load affordability data');
        } finally {
            setLoading(false);
        }
    }

    function renderMarkers(zones: AffordabilityZone[]) {
        if (!layerRef.current) {
            layerRef.current = L.layerGroup().addTo(map);
        }
        layerRef.current.clearLayers();

        zones.forEach(zone => {
            if (!zone.lat || !zone.lon) return;

            const marker = L.circleMarker([zone.lat, zone.lon], {
                radius: Math.max(8, Math.min(15, (zone.population || 1000) / 2000)),
                fillColor: zone.color,
                fillOpacity: 0.8,
                color: '#000',
                weight: 1,
                opacity: 0.6
            });

            const burdenColor = zone.burden_pct > 5 ? '#dc2626' :
                zone.burden_pct > 2 ? '#f59e0b' : '#22c55e';

            marker.bindPopup(`
                <div style="min-width: 200px;">
                    <div style="font-weight: bold; font-size: 14px; margin-bottom: 8px; color: ${zone.color};">
                        ${zone.status === 'AFFORDABLE' ? '✅' : '🚫'} ZCTA ${zone.zcta}
                    </div>
                    <div style="font-size: 12px; line-height: 1.6;">
                        <div><strong>ISP:</strong> ${zone.isp}</div>
                        <div><strong>Monthly Cost:</strong> $${zone.internet_cost}/mo</div>
                        <div><strong>Median Income:</strong> $${zone.median_income.toLocaleString()}/yr</div>
                        <hr style="margin: 6px 0; border-color: #e5e7eb;" />
                        <div style="color: ${burdenColor}; font-weight: 600;">
                            Cost Burden: ${zone.burden_pct}% of income
                        </div>
                        <div style="font-size: 11px; color: #6b7280; margin-top: 4px;">
                            UN Affordability Standard: < 2%
                        </div>
                    </div>
                </div>
            `);

            layerRef.current?.addLayer(marker);
        });
    }

    // Top unaffordable areas
    const worstAreas = useMemo(() => {
        if (!data) return [];
        return data.zones
            .filter(z => !z.is_affordable)
            .sort((a, b) => b.burden_pct - a.burden_pct)
            .slice(0, 5);
    }, [data]);

    if (!visible) return null;

    return (
        <div style={{
            position: 'absolute',
            top: '10px',
            left: '10px',
            zIndex: 1000,
            backgroundColor: 'white',
            borderRadius: '12px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
            width: '320px',
            maxHeight: '85vh',
            overflow: 'auto'
        }}>
            {/* Header */}
            <div style={{
                background: 'linear-gradient(135deg, #7c3aed 0%, #a855f7 100%)',
                color: 'white',
                padding: '16px',
                borderRadius: '12px 12px 0 0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <div>
                    <div style={{ fontWeight: 'bold', fontSize: '16px' }}>💰 Digital Equity</div>
                    <div style={{ fontSize: '11px', opacity: 0.9 }}>Affordability Analysis</div>
                </div>
                <button
                    onClick={onToggle}
                    style={{
                        background: 'rgba(255,255,255,0.2)',
                        border: 'none',
                        color: 'white',
                        width: '28px',
                        height: '28px',
                        borderRadius: '50%',
                        cursor: 'pointer',
                        fontSize: '16px'
                    }}
                >×</button>
            </div>

            {/* Content */}
            <div style={{ padding: '16px' }}>
                {loading && (
                    <div style={{ textAlign: 'center', padding: '20px', color: '#6b7280' }}>
                        Loading affordability data...
                    </div>
                )}

                {error && (
                    <div style={{
                        padding: '12px',
                        backgroundColor: '#fee2e2',
                        color: '#dc2626',
                        borderRadius: '8px',
                        fontSize: '13px'
                    }}>
                        ⚠️ {error}
                    </div>
                )}

                {data && (
                    <>
                        {/* Summary Stats */}
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: '1fr 1fr',
                            gap: '12px',
                            marginBottom: '16px'
                        }}>
                            <div style={{
                                backgroundColor: '#dcfce7',
                                padding: '12px',
                                borderRadius: '8px',
                                textAlign: 'center'
                            }}>
                                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#16a34a' }}>
                                    {data.summary.affordable}
                                </div>
                                <div style={{ fontSize: '11px', color: '#166534' }}>Affordable</div>
                            </div>
                            <div style={{
                                backgroundColor: '#fee2e2',
                                padding: '12px',
                                borderRadius: '8px',
                                textAlign: 'center'
                            }}>
                                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#dc2626' }}>
                                    {data.summary.unaffordable}
                                </div>
                                <div style={{ fontSize: '11px', color: '#991b1b' }}>Unaffordable</div>
                            </div>
                        </div>

                        {/* Affordability Rate */}
                        <div style={{
                            backgroundColor: '#f3f4f6',
                            padding: '12px',
                            borderRadius: '8px',
                            marginBottom: '16px'
                        }}>
                            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>
                                Affordability Rate
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <div style={{
                                    flex: 1,
                                    height: '8px',
                                    backgroundColor: '#e5e7eb',
                                    borderRadius: '4px',
                                    overflow: 'hidden'
                                }}>
                                    <div style={{
                                        width: `${data.summary.affordable_pct}%`,
                                        height: '100%',
                                        backgroundColor: data.summary.affordable_pct > 50 ? '#22c55e' : '#ef4444',
                                        transition: 'width 0.5s ease'
                                    }} />
                                </div>
                                <span style={{ fontWeight: 'bold', color: '#374151', fontSize: '14px' }}>
                                    {data.summary.affordable_pct}%
                                </span>
                            </div>
                        </div>

                        {/* Worst Cases */}
                        {worstAreas.length > 0 && (
                            <div>
                                <div style={{
                                    fontSize: '13px',
                                    fontWeight: '600',
                                    color: '#374151',
                                    marginBottom: '8px'
                                }}>
                                    🚨 Highest Cost Burden
                                </div>
                                {worstAreas.map((zone, i) => (
                                    <div
                                        key={zone.zcta}
                                        onClick={() => {
                                            if (zone.lat && zone.lon) {
                                                map.flyTo([zone.lat, zone.lon], 10);
                                            }
                                        }}
                                        style={{
                                            padding: '10px',
                                            backgroundColor: i === 0 ? '#fef2f2' : '#f9fafb',
                                            borderRadius: '6px',
                                            marginBottom: '6px',
                                            cursor: 'pointer',
                                            borderLeft: `3px solid ${i === 0 ? '#dc2626' : '#f59e0b'}`,
                                            transition: 'transform 0.2s'
                                        }}
                                        onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.02)'}
                                        onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
                                    >
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <div>
                                                <div style={{ fontWeight: '600', fontSize: '13px' }}>
                                                    ZCTA {zone.zcta}
                                                </div>
                                                <div style={{ fontSize: '11px', color: '#6b7280' }}>
                                                    {zone.isp} @ ${zone.internet_cost}/mo
                                                </div>
                                            </div>
                                            <div style={{
                                                fontWeight: 'bold',
                                                color: zone.burden_pct > 10 ? '#dc2626' : '#f59e0b',
                                                fontSize: '14px'
                                            }}>
                                                {zone.burden_pct}%
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Legend */}
                        <div style={{
                            marginTop: '16px',
                            padding: '12px',
                            backgroundColor: '#f9fafb',
                            borderRadius: '8px',
                            fontSize: '11px',
                            color: '#6b7280'
                        }}>
                            <div style={{ fontWeight: '600', marginBottom: '6px' }}>Legend</div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                                <span style={{ display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#22c55e' }} />
                                Affordable (&lt;2% of income)
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span style={{ display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#ef4444' }} />
                                Unaffordable (≥2% of income)
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
