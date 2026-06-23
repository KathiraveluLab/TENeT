import React, { useEffect, useState, useRef, useMemo } from 'react';
import { useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { ChoroplethLayer } from './ChoroplethLayer';
import {
    PerformanceTile,
    AffordabilityZone,
    PerformanceFilterType,
    fetchPerformance,
    fetchAffordability
} from '../api/catApi';
import { getScenarioCost, getTrafficLightStatus, AFFORDABILITY_BURDEN_THRESHOLD } from '../utils/trafficLight';

interface PerformanceLayerProps {
    visible: boolean;
    onToggle: () => void;
    onModeChange?: (isGapMode: boolean) => void;
}

const DETAIL_ZOOM_THRESHOLD = 8;

export default function PerformanceLayer({ visible, onToggle, onModeChange }: PerformanceLayerProps) {
    const [tiles, setTiles] = useState<PerformanceTile[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [zoomLevel, setZoomLevel] = useState(5);

    // UI State for Filters
    const [filterMode, setFilterMode] = useState<PerformanceFilterType>('combined');
    const [useStarlink, setUseStarlink] = useState(false);
    const [showRegions, setShowRegions] = useState(false); // Toggle for choropleth vs dots

    // Data State
    const [affordabilityData, setAffordabilityData] = useState<AffordabilityZone[]>([]);

    const canvasLayerRef = useRef<L.LayerGroup | null>(null);
    const map = useMap();

    useMapEvents({
        zoomend: () => setZoomLevel(map.getZoom())
    });

    useEffect(() => {
        setZoomLevel(map.getZoom());
    }, [map]);

    useEffect(() => {
        if (visible) {
            loadData();
        } else {
            if (canvasLayerRef.current) {
                canvasLayerRef.current.clearLayers();
            }
        }
    }, [visible]);

    useEffect(() => {
        if (onModeChange) {
            onModeChange(visible);
        }
    }, [visible, onModeChange]);

    const getScenarioBurden = (afford: AffordabilityZone | undefined, lat: number): number | null => {
        if (!afford || !afford.monthly_income || afford.monthly_income <= 0) return null;
        const cost = getScenarioCost(lat, useStarlink);
        return (cost / afford.monthly_income) * 100;
    };

    function getAffordabilityForTile(lat: number, lon: number): AffordabilityZone | undefined {
        if (!affordabilityData.length) return undefined;
        let nearest: AffordabilityZone | undefined;
        let minDist = Infinity;
        const MAX_DIST_DEG = 0.2;
        for (const zone of affordabilityData) {
            if (!zone.lat || !zone.lon) continue;
            const dLat = zone.lat - lat;
            const dLon = zone.lon - lon;
            const distSq = dLat * dLat + dLon * dLon;
            if (distSq < minDist && distSq < MAX_DIST_DEG * MAX_DIST_DEG) {
                minDist = distSq;
                nearest = zone;
            }
        }
        return nearest;
    }

    // --- Traffic Light Logic ---

    const getTrafficLightStatusForTile = (
        tile: PerformanceTile,
        burden: number | null,
        scenarioCost: number
    ): 'RED' | 'ORANGE' | 'YELLOW' | 'GREEN' | 'GRAY' => {
        return getTrafficLightStatus(tile.avg_d_mbps || 0, tile.avg_lat_ms || 0, burden, scenarioCost);
    };


    const visibleTiles = useMemo(() => {
        return tiles.filter(t => {
            if (!t.lat || !t.lon) return false;
            // Basic Bounds Check (Alaska)
            if (t.lat >= 59 && t.lat <= 61 && t.lon >= -134 && t.lon <= -130) return false; // BC Border
            return true;
        });
    }, [tiles]);

    // Re-render map
    useEffect(() => {
        if (visible && tiles.length > 0) {
            renderCanvasMarkers(visibleTiles);
        }
    }, [visible, visibleTiles, zoomLevel, useStarlink, affordabilityData, filterMode]); // Dependencies updated

    async function loadData() {
        try {
            setLoading(true);
            setError(null);
            const [perfData, affordData] = await Promise.all([
                fetchPerformance(),
                fetchAffordability().catch(() => ({ zones: [] }))
            ]);
            setTiles(perfData.tiles);
            setAffordabilityData(affordData.zones);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load data');
        } finally {
            setLoading(false);
        }
    }

    function renderCanvasMarkers(tilesToRender: PerformanceTile[]) {
        if (canvasLayerRef.current) {
            canvasLayerRef.current.clearLayers();
            map.removeLayer(canvasLayerRef.current);
        }

        const canvasRenderer = L.canvas({ padding: 0.5 });
        const layerGroup = L.layerGroup();
        const isDetailView = zoomLevel >= DETAIL_ZOOM_THRESHOLD;

        tilesToRender.forEach(tile => {
            if (!tile.lat || !tile.lon) return;

            const afford = getAffordabilityForTile(tile.lat, tile.lon);
            const scenarioCost = getScenarioCost(tile.lat, useStarlink);
            const burdenPct = getScenarioBurden(afford, tile.lat);

            let markerColor = '#ccc';
            let markerRadius = isDetailView ? 6 : Math.min(20, Math.max(4, (tile.tests / 5)));
            let showTile = true;

            // --- FILTER LOGIC ---
            if (filterMode === 'affordability') {
                const isRuralTier = scenarioCost >= 400;

                if (burdenPct === null) {
                    markerColor = isRuralTier ? '#f97316' : '#94a3b8';
                    markerRadius = 4;
                } else if (isRuralTier) {
                    if (burdenPct >= 2) {
                        markerColor = '#EF4444'; // Rose Red - Unattainable
                        markerRadius = 5;        // Larger for problems
                    } else {
                        markerColor = '#f97316'; // Orange
                        markerRadius = 4;
                    }
                } else {
                    if (burdenPct < 1) {
                        markerColor = '#10B981'; // Emerald - Affordable
                        markerRadius = 3;        // Smaller for good
                    } else if (burdenPct < 2) {
                        markerColor = '#F59E0B'; // Amber - Burdened
                        markerRadius = 4;
                    } else {
                        markerColor = '#EF4444'; // Rose - Unattainable
                        markerRadius = 5;        // Larger for problems
                    }
                }

            } else if (filterMode === 'latency') {
                const lat = tile.avg_lat_ms || 0;
                if (lat < 50) {
                    markerColor = '#10B981'; // Emerald
                    markerRadius = 3;        // Small for good
                } else if (lat < 150) {
                    markerColor = '#F59E0B'; // Amber
                    markerRadius = 4;
                } else {
                    markerColor = '#EF4444'; // Rose
                    markerRadius = 5;        // Large for problems
                }

            } else {
                // 'combined' - Traffic Light Logic
                const status = getTrafficLightStatusForTile(tile, burdenPct, scenarioCost);
                switch (status) {
                    case 'RED':
                        markerColor = '#EF4444';  // Rose
                        markerRadius = 5;
                        break;
                    case 'ORANGE':
                        markerColor = '#f97316';
                        markerRadius = 4;
                        break;
                    case 'YELLOW':
                        markerColor = '#F59E0B';  // Amber
                        markerRadius = 4;
                        break;
                    case 'GREEN':
                        markerColor = '#10B981';  // Emerald
                        markerRadius = 3;
                        break;
                    default:
                        markerColor = '#94a3b8';
                        markerRadius = 4;
                }
            }

            // Gemstone effect marker
            const marker = L.circleMarker([tile.lat, tile.lon], {
                radius: markerRadius,       // Dynamic based on status
                fillColor: markerColor,
                fillOpacity: 0.65,          // KEY: Lower opacity for gemstone effect
                color: '#ffffff',           // Pure white stroke
                weight: 1.5,                // Thicker stroke for definition
                opacity: 0.9,               // Almost solid border
                renderer: canvasRenderer
            });

            // Build Popup
            const latencyDisplay = tile.avg_lat_ms ? `${tile.avg_lat_ms.toFixed(0)} ms` : 'N/A';
            const costDisplay = burdenPct ? `${burdenPct.toFixed(1)}%` : 'N/A';
            const status = getTrafficLightStatusForTile(tile, burdenPct, scenarioCost);

            let capabilityLabel = "";
            if (status === 'RED') capabilityLabel = "Async / Text Only";
            else if (status === 'ORANGE') capabilityLabel = "Expensive Infrastructure";
            else if (status === 'YELLOW') capabilityLabel = "Audio / Low-Res Video";
            else if (status === 'GREEN') capabilityLabel = "HD Video Ready";

            marker.bindPopup(`
                <div style="min-width: 200px; font-family: sans-serif;">
                    <div style="margin-bottom: 8px; font-weight: bold; color: ${markerColor}">
                        ${filterMode === 'combined' ? capabilityLabel : 'Location Details'}
                    </div>
                    
                    <div style="background: #f3f4f6; padding: 6px; border-radius: 4px; margin-bottom: 8px; font-size: 11px;">
                         <div><strong>Latency:</strong> ${latencyDisplay}</div>
                         <div><strong>Burden:</strong> ${costDisplay} of Income</div>
                         <div><strong>Speed:</strong> ${tile.avg_d_mbps?.toFixed(1) ?? 'N/A'} Mbps</div>
                    </div>

                    <div style="font-size: 10px; color: #6b7280;">
                         Generated by Gap Hunter v2
                    </div>
                </div>
            `);

            layerGroup.addLayer(marker);
        });

        layerGroup.addTo(map);
        canvasLayerRef.current = layerGroup;
    }

    if (!visible) return null;

    return (
        <>
            <div style={panelStyle}>
                {/* Header */}
                <div style={headerStyle} onClick={onToggle}>
                    <span>Gap Hunter</span>
                    <span style={{ fontSize: '10px', cursor: 'pointer' }}>✕</span>
                </div>

                {/* Filter Dropdown */}
                <div style={{ padding: '10px 12px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '11px', fontWeight: '600', color: '#64748b', marginBottom: '4px' }}>
                        ACTIVE LAYER
                    </div>
                    <select
                        value={filterMode}
                        onChange={(e) => setFilterMode(e.target.value as PerformanceFilterType)}
                        style={{
                            width: '100%',
                            padding: '6px',
                            borderRadius: '4px',
                            border: '1px solid #cbd5e1',
                            fontSize: '12px',
                            marginBottom: '10px',
                            cursor: 'pointer'
                        }}
                    >
                        <option value="combined">Combined Feasibility (Master)</option>
                        <option value="affordability">Affordability Cost/Income</option>
                        <option value="latency">Latency (Ping)</option>
                    </select>

                    {/* Starlink Toggle */}
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '12px' }}>
                        <input
                            type="checkbox"
                            checked={useStarlink}
                            onChange={(e) => setUseStarlink(e.target.checked)}
                            style={{ accentColor: '#3b82f6' }}
                        />
                        <span>Simulate Starlink LEO ($120/mo)</span>
                    </label>

                    {/* Region Toggle */}
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '12px', marginTop: '8px' }}>
                        <input
                            type="checkbox"
                            checked={showRegions}
                            onChange={(e) => setShowRegions(e.target.checked)}
                            style={{ accentColor: '#10b981' }}
                        />
                        <span>Show Region Polygons</span>
                    </label>
                </div>

                {/* Legend - Dynamic based on Filter */}
                <div style={{ padding: '10px 12px', fontSize: '11px' }}>
                    <div style={{ fontWeight: '600', marginBottom: '6px' }}>Legend</div>

                    {filterMode === 'combined' && (
                        <>
                            <LegendItem color="#22c55e" label="HD Video Ready" sub="Urban, Fast + Affordable" />
                            <LegendItem color="#facc15" label="Audio/Low-Res" sub="Medium Latency" />
                            <LegendItem color="#f97316" label="Expensive Infrastructure" sub="Rural $450/mo tier" />
                            <LegendItem color="#ef4444" label="Async Only" sub="High Latency or Unaffordable" />
                            <LegendItem color="#9ca3af" label="Insufficient Data" sub="Missing metrics" />
                        </>
                    )}
                    {filterMode === 'affordability' && (
                        <>
                            <LegendItem color="#22c55e" label="Affordable (<1%)" sub="Urban, low burden" />
                            <LegendItem color="#facc15" label="Burdened (1-2%)" sub="Moderate burden" />
                            <LegendItem color="#f97316" label="Expensive Infrastructure" sub="Rural $450/mo tier" />
                            <LegendItem color="#ef4444" label="Unattainable (>2%)" sub="High cost burden" />
                            <LegendItem color="#e5e7eb" border="#374151" label="No Income Data" sub="Urban, no census data" />
                        </>
                    )}
                    {filterMode === 'latency' && (
                        <>
                            <LegendItem color="#22c55e" label="Fast (<50ms)" sub="HD video capable" />
                            <LegendItem color="#facc15" label="Medium (50-150ms)" sub="Audio/low-res video" />
                            <LegendItem color="#ef4444" label="Slow (>150ms)" sub="Async only" />
                        </>
                    )}
                </div>

                <div style={{ padding: '6px 12px', fontSize: '9px', color: '#9ca3af', backgroundColor: '#f9fafb', borderTop: '1px solid #e5e7eb' }}>
                    Traffic Light System v1.0
                </div>
            </div>

            {/* Choropleth Region Layer - rendered when showRegions is enabled */}
            {
                showRegions && (
                    <ChoroplethLayer
                        visible={showRegions}
                        tiles={tiles}
                        affordabilityData={affordabilityData}
                        useStarlink={useStarlink}
                    />
                )
            }
        </>
    );
}

// Legend Component Helper
const LegendItem = ({ color, border, label, sub }: { color: string, border?: string, label: string, sub?: string }) => (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '6px' }}>
        <div style={{
            width: '12px',
            height: '12px',
            borderRadius: '50%',
            background: color,
            border: border ? `2px solid ${border}` : 'none',
            flexShrink: 0,
            marginTop: '2px',
            boxSizing: 'border-box'
        }} />
        <div>
            <div style={{ color: '#334155', fontWeight: '500' }}>{label}</div>
            {sub && <div style={{ color: '#64748b', fontSize: '10px' }}>{sub}</div>}
        </div>
    </div>
);

const panelStyle: React.CSSProperties = {
    position: 'absolute',
    top: '20px',
    left: '20px',
    zIndex: 1000,
    minWidth: '280px',
    // Glassmorphism effect
    background: 'rgba(255, 255, 255, 0.92)',
    backdropFilter: 'blur(12px)',
    WebkitBackdropFilter: 'blur(12px)',
    border: '1px solid rgba(255, 255, 255, 0.3)',
    boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.12)',
    borderRadius: '12px',
    fontSize: '13px',
    overflow: 'hidden'
};

// Clean header - no dark bar (Flaw 3 fix)
const headerStyle: React.CSSProperties = {
    padding: '14px 16px',
    borderBottom: '1px solid rgba(0, 0, 0, 0.06)',
    fontSize: '15px',
    fontWeight: '700',
    letterSpacing: '-0.02em',
    color: '#0f172a',  // Dark text on white, no background
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    cursor: 'pointer'
};
