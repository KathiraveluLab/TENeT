import React, { useEffect, useState, useRef, useMemo } from 'react';
import { useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { ChoroplethLayer } from './ChoroplethLayer';
import {
    PerformanceTile,
    PerformanceSummary,
    TopGap,
    AffordabilityZone,
    PerformanceFilterType, // Import the new type
    fetchPerformance,
    fetchPerformanceSummary,
    fetchTopGaps,
    fetchAffordability,
    getSpeedColor
} from '../api/catApi';

interface PerformanceLayerProps {
    visible: boolean;
    onToggle: () => void;
    onModeChange?: (isGapMode: boolean) => void;
}

const DETAIL_ZOOM_THRESHOLD = 8;
const TELEHEALTH_THRESHOLD_MBPS = 25;

export default function PerformanceLayer({ visible, onToggle, onModeChange }: PerformanceLayerProps) {
    const [tiles, setTiles] = useState<PerformanceTile[]>([]);
    const [summary, setSummary] = useState<PerformanceSummary | null>(null);
    const [topGaps, setTopGaps] = useState<TopGap[]>([]);
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

    // Thresholds
    const CRITICAL_SPEED_MBPS = 5;
    const CRITICAL_LATENCY_MS = 150; // "Traffic Light" Red Zone
    const WARNING_LATENCY_MS = 100;  // "Traffic Light" Yellow Zone
    const AFFORDABILITY_BURDEN_THRESHOLD = 2.0;

    // --- Helper Functions ---

    const getScenarioCost = (afford: AffordabilityZone | undefined, lat: number): number => {
        if (useStarlink) return 120;
        if (lat > 63) return 450;
        return 125;
    };

    const getScenarioBurden = (afford: AffordabilityZone | undefined, lat: number): number | null => {
        if (!afford || !afford.monthly_income || afford.monthly_income <= 0) return null;
        const cost = getScenarioCost(afford, lat);
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

    const getTrafficLightStatus = (
        tile: PerformanceTile,
        burden: number | null,
        scenarioCost: number
    ): 'RED' | 'ORANGE' | 'YELLOW' | 'GREEN' | 'GRAY' => {
        const latency = tile.avg_lat_ms || 0;
        const speed = tile.avg_d_mbps || 0;
        const isRuralTier = scenarioCost >= 400; // $450/mo rural pricing

        // RED ZONE: High Latency OR Rural + Unaffordable OR Unusable Speed
        if (latency > CRITICAL_LATENCY_MS || speed < CRITICAL_SPEED_MBPS) {
            return 'RED';
        }

        // RED for high burden (urban or rural)
        if (burden !== null && burden > AFFORDABILITY_BURDEN_THRESHOLD) {
            return 'RED';
        }

        // ORANGE ZONE: Rural areas with expensive infrastructure (even if fast)
        if (isRuralTier) {
            return 'ORANGE'; // Expensive infrastructure regardless of speed/latency
        }

        // YELLOW ZONE: Medium Latency (urban areas only reach here)
        if (latency > 50 && latency <= CRITICAL_LATENCY_MS) {
            return 'YELLOW';
        }

        // GREEN ZONE: Low Latency AND Affordable AND Good Speed AND Urban
        if (latency <= 50 && (burden === null || burden <= AFFORDABILITY_BURDEN_THRESHOLD) && speed >= 25) {
            return 'GREEN';
        }

        return 'GRAY';
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
            const [perfData, summaryData, gapsData, affordData] = await Promise.all([
                fetchPerformance(),
                fetchPerformanceSummary(),
                fetchTopGaps(10),
                fetchAffordability().catch(() => ({ zones: [] }))
            ]);
            setTiles(perfData.tiles);
            setSummary(summaryData);
            setTopGaps(gapsData.gaps);
            setAffordabilityData(affordData.zones);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load data');
        } finally {
            setLoading(false);
        }
    }

    function handleGapClick(lat: number, lon: number) {
        map.flyTo([lat, lon], 13, { duration: 1.5 });
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
            const scenarioCost = getScenarioCost(afford, tile.lat);
            const burdenPct = getScenarioBurden(afford, tile.lat);

            let markerColor = '#ccc';
            let markerRadius = isDetailView ? 6 : Math.min(20, Math.max(4, (tile.tests / 5)));
            let showTile = true;

            // --- FILTER LOGIC ---
            if (filterMode === 'affordability') {
                // Check if this is a "rural tier" location with expensive infrastructure
                const isRuralTier = scenarioCost >= 400; // $450/mo rural pricing

                if (burdenPct === null) {
                    // No income data - but if rural, assume expensive
                    markerColor = isRuralTier ? '#f97316' : '#e5e7eb'; // Orange for rural unknown, Gray otherwise
                } else if (isRuralTier) {
                    // RURAL AREAS: Floor at Yellow minimum (never Green)
                    // Rationale: $450/mo is objectively expensive infrastructure
                    if (burdenPct >= 2) {
                        markerColor = '#ef4444'; // Red - Unattainable
                    } else {
                        markerColor = '#f97316'; // Orange - Expensive Infrastructure
                    }
                } else {
                    // URBAN AREAS: Standard burden thresholds
                    if (burdenPct < 1) {
                        markerColor = '#22c55e'; // Green - Affordable
                    } else if (burdenPct < 2) {
                        markerColor = '#facc15'; // Yellow - Burdened
                    } else {
                        markerColor = '#ef4444'; // Red - Unattainable
                    }
                }
                markerRadius = isDetailView ? 6 : 4;

            } else if (filterMode === 'latency') {
                const lat = tile.avg_lat_ms || 0;
                if (lat < 50) markerColor = '#22c55e'; // Green
                else if (lat < 150) markerColor = '#facc15'; // Yellow
                else markerColor = '#ef4444'; // Red
                markerRadius = isDetailView ? 6 : 4;

            } else {
                // 'combined' - Traffic Light Logic (Master Logic)
                const status = getTrafficLightStatus(tile, burdenPct, scenarioCost);
                switch (status) {
                    case 'RED': markerColor = '#ef4444'; break;
                    case 'ORANGE': markerColor = '#f97316'; break;
                    case 'YELLOW': markerColor = '#facc15'; break;
                    case 'GREEN': markerColor = '#22c55e'; break;
                    default: markerColor = '#9ca3af';
                }
                markerRadius = isDetailView ? 6 : 4;
            }

            const marker = L.circleMarker([tile.lat, tile.lon], {
                radius: markerRadius,
                fillColor: markerColor,
                fillOpacity: 0.7,
                color: markerColor === '#22c55e' ? '#15803d' : '#000', // Green border for green, black otherwise
                weight: 1,
                renderer: canvasRenderer
            });

            // Build Popup
            const latencyDisplay = tile.avg_lat_ms ? `${tile.avg_lat_ms.toFixed(0)} ms` : 'N/A';
            const costDisplay = burdenPct ? `${burdenPct.toFixed(1)}%` : 'N/A';
            const status = getTrafficLightStatus(tile, burdenPct, scenarioCost);

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
    top: '10px',
    left: '10px',
    backgroundColor: 'white',
    borderRadius: '8px',
    boxShadow: '0 2px 12px rgba(0,0,0,0.2)',
    zIndex: 1000,
    minWidth: '220px',
    fontSize: '13px',
    overflow: 'hidden'
};

const headerStyle: React.CSSProperties = {
    padding: '10px 12px',
    backgroundColor: '#0f172a',
    color: 'white',
    fontSize: '14px',
    fontWeight: '700',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    cursor: 'pointer'
};
