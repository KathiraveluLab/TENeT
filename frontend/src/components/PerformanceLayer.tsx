import { useEffect, useState, useRef, useMemo } from 'react';
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
import { errorMessage, isAbortError } from '../api/http';
import { escapeHtml } from '../utils/escapeHtml';
import { getScenarioCost, getTrafficLightStatus } from '../utils/trafficLight';
import IconButton from './ui/IconButton';
import './PerformanceLayer.css';

interface PerformanceLayerProps {
    visible: boolean;
    onToggle: () => void;
}

const DETAIL_ZOOM_THRESHOLD = 8;

export default function PerformanceLayer({ visible, onToggle }: PerformanceLayerProps) {
    const [tiles, setTiles] = useState<PerformanceTile[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [partialWarning, setPartialWarning] = useState<string | null>(null);
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
            const controller = new AbortController();
            loadData(controller.signal);
            return () => controller.abort();
        } else {
            if (canvasLayerRef.current) {
                canvasLayerRef.current.clearLayers();
            }
        }
    }, [visible]);

    const getScenarioBurden = (afford: AffordabilityZone | undefined, lat: number): number | null => {
        if (!afford || afford.monthly_income <= 0) return null;
        const cost = getScenarioCost(lat, useStarlink);
        return (cost / afford.monthly_income) * 100;
    };

    function getAffordabilityForTile(lat: number, lon: number): AffordabilityZone | undefined {
        if (!affordabilityData.length) return undefined;
        let nearest: AffordabilityZone | undefined;
        let minDist = Infinity;
        const MAX_DIST_DEG = 0.2;
        for (const zone of affordabilityData) {
            if (zone.lat === null || zone.lon === null) continue;
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
        if (tile.avg_d_mbps === null || tile.avg_lat_ms === null || burden === null) return 'GRAY';
        return getTrafficLightStatus(tile.avg_d_mbps, tile.avg_lat_ms, burden, scenarioCost);
    };


    const visibleTiles = useMemo(() => {
        return tiles.filter(t => {
            if (!Number.isFinite(t.lat) || !Number.isFinite(t.lon)) return false;
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

    async function loadData(signal: AbortSignal) {
        try {
            setLoading(true);
            setError(null);
            setPartialWarning(null);
            const [performanceResult, affordabilityResult] = await Promise.allSettled([
                fetchPerformance(undefined, undefined, 1, signal),
                fetchAffordability(120, 2, signal),
            ]);
            if (signal.aborted) return;
            if (performanceResult.status === 'rejected') {
                throw performanceResult.reason;
            }
            setTiles(performanceResult.value.tiles);
            if (affordabilityResult.status === 'fulfilled') {
                setAffordabilityData(affordabilityResult.value.zones);
            } else {
                setAffordabilityData([]);
                setPartialWarning(
                    errorMessage(affordabilityResult.reason, 'Affordability data unavailable'),
                );
            }
        } catch (caught: unknown) {
            if (!isAbortError(caught)) {
                setError(errorMessage(caught, 'Failed to load data'));
            }
        } finally {
            if (!signal.aborted) setLoading(false);
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
            if (!Number.isFinite(tile.lat) || !Number.isFinite(tile.lon)) return;

            const afford = getAffordabilityForTile(tile.lat, tile.lon);
            const scenarioCost = getScenarioCost(tile.lat, useStarlink);
            const burdenPct = getScenarioBurden(afford, tile.lat);

            let markerColor = '#ccc';
            let markerRadius = isDetailView ? 6 : Math.min(20, Math.max(4, (tile.tests / 5)));
            // --- FILTER LOGIC ---
            if (filterMode === 'affordability') {
                const isRuralTier = scenarioCost >= 400;

                if (burdenPct === null) {
                    markerColor = '#94a3b8';
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
                const lat = tile.avg_lat_ms;
                if (lat === null) {
                    markerColor = '#94a3b8';
                    markerRadius = 4;
                } else if (lat < 50) {
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
            const latencyDisplay = tile.avg_lat_ms !== null ? `${tile.avg_lat_ms.toFixed(0)} ms` : 'N/A';
            const costDisplay = burdenPct !== null ? `${burdenPct.toFixed(1)}%` : 'N/A';
            const speedDisplay = tile.avg_d_mbps !== null ? `${tile.avg_d_mbps.toFixed(1)} Mbps` : 'N/A';
            const status = getTrafficLightStatusForTile(tile, burdenPct, scenarioCost);

            let capabilityLabel = "Insufficient Data";
            if (status === 'RED') capabilityLabel = "Async / Text Only";
            else if (status === 'ORANGE') capabilityLabel = "Expensive Infrastructure";
            else if (status === 'YELLOW') capabilityLabel = "Audio / Low-Res Video";
            else if (status === 'GREEN') capabilityLabel = "HD Video Ready";

            marker.bindPopup(`
                <div class="performance-popup" style="--popup-color:${markerColor}">
                    <div class="performance-popup__title">
                        ${escapeHtml(filterMode === 'combined' ? capabilityLabel : 'Location Details')}
                    </div>
                    <div class="performance-popup__metrics">
                         <div><strong>Latency:</strong> ${escapeHtml(latencyDisplay)}</div>
                         <div><strong>Burden:</strong> ${escapeHtml(costDisplay)} of Income</div>
                         <div><strong>Speed:</strong> ${escapeHtml(speedDisplay)}</div>
                    </div>
                    <div class="performance-popup__source">
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
            <div className="performance-control-panel">
                {/* Header */}
                <div className="performance-control-header">
                    <span>Gap Hunter</span>
                    <IconButton
                        icon="×"
                        size="small"
                        onClick={onToggle}
                        aria-label="Close Gap Hunter"
                    />
                </div>

                {loading && <div className="performance-control-state" role="status">Loading measured performance…</div>}
                {error && <div className="performance-control-state is-error" role="alert">{error}</div>}
                {partialWarning && (
                    <div className="performance-control-state is-warning" role="status">
                        Affordability inputs unavailable; affected locations are shown as insufficient data.
                    </div>
                )}

                {/* Filter Dropdown */}
                <div className="performance-control-settings">
                    <div className="performance-control-kicker">
                        ACTIVE LAYER
                    </div>
                    <select
                        value={filterMode}
                        onChange={(e) => setFilterMode(e.target.value as PerformanceFilterType)}
                        className="performance-control-select"
                    >
                        <option value="combined">Combined Feasibility (Master)</option>
                        <option value="affordability">Affordability Cost/Income</option>
                        <option value="latency">Latency (Ping)</option>
                    </select>

                    {/* Starlink Toggle */}
                    <label className="performance-control-toggle">
                        <input
                            type="checkbox"
                            checked={useStarlink}
                            onChange={(e) => setUseStarlink(e.target.checked)}
                            className="is-blue"
                        />
                        <span>Simulate Starlink LEO ($120/mo)</span>
                    </label>

                    {/* Region Toggle */}
                    <label className="performance-control-toggle is-spaced">
                        <input
                            type="checkbox"
                            checked={showRegions}
                            onChange={(e) => setShowRegions(e.target.checked)}
                            className="is-green"
                        />
                        <span>Show Region Polygons</span>
                    </label>
                </div>

                {/* Legend - Dynamic based on Filter */}
                <div className="performance-legend">
                    <div className="performance-legend__title">Legend</div>

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

                <div className="performance-control-footer">
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
    <div className="performance-legend-item">
        <div
            className={`performance-legend-swatch${border ? ' has-border' : ''}`}
            style={{ backgroundColor: color, borderColor: border }}
        />
        <div>
            <div className="performance-legend-label">{label}</div>
            {sub && <div className="performance-legend-note">{sub}</div>}
        </div>
    </div>
);
