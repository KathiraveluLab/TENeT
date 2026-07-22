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
import { getScenarioCost, getTrafficLightStatus } from '../utils/trafficLight';
import IconButton from './ui/IconButton';
import './PerformanceLayer.css';
import { PerformanceCanvasLayer } from './PerformanceCanvasLayer';
import { errorMessage, isAbortError } from '../api/http';

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
        }
    }, [visible]);




    const visibleTiles = useMemo(() => {
        return tiles.filter(t => {
            if (!Number.isFinite(t.lat) || !Number.isFinite(t.lon)) return false;
            // Basic Bounds Check (Alaska)
            if (t.lat >= 59 && t.lat <= 61 && t.lon >= -134 && t.lon <= -130) return false; // BC Border
            return true;
        });
    }, [tiles]);



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
            {showRegions && (
                <ChoroplethLayer
                    visible={showRegions}
                    tiles={tiles}
                    affordabilityData={affordabilityData}
                    useStarlink={useStarlink}
                />
            )}
            {!showRegions && visibleTiles.length > 0 && (
                <PerformanceCanvasLayer
                    visibleTiles={visibleTiles}
                    affordabilityData={affordabilityData}
                    useStarlink={useStarlink}
                    filterMode={filterMode}
                    zoomLevel={zoomLevel}
                />
            )}
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
