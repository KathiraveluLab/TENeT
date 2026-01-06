import React, { useEffect, useState, useRef, useMemo } from 'react';
import { useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import {
    PerformanceTile,
    PerformanceSummary,
    TopGap,
    AffordabilityZone,
    fetchPerformance,
    fetchPerformanceSummary,
    fetchTopGaps,
    fetchAffordability,
    getSpeedColor
} from '../api/catApi';

interface PerformanceLayerProps {
    visible: boolean;
    onToggle: () => void;
    onModeChange?: (isGapMode: boolean) => void;  // Callback to notify parent of mode changes
}

const DETAIL_ZOOM_THRESHOLD = 8;
const TELEHEALTH_THRESHOLD_MBPS = 25;

/**
 * Gap Hunter: Performance Layer focused on identifying underserved areas
 * Features:
 * - Filter to show only service gaps
 * - Top priority gaps with location names (reverse geocoded)
 * - Clickable rows to fly to gap location
 */
export default function PerformanceLayer({ visible, onToggle, onModeChange }: PerformanceLayerProps) {
    const [tiles, setTiles] = useState<PerformanceTile[]>([]);
    const [summary, setSummary] = useState<PerformanceSummary | null>(null);
    const [topGaps, setTopGaps] = useState<TopGap[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [zoomLevel, setZoomLevel] = useState(5);
    const [showGapsOnly, setShowGapsOnly] = useState(true);
    const [affordabilityData, setAffordabilityData] = useState<AffordabilityZone[]>([]);
    const [useStarlink, setUseStarlink] = useState(false);
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

    // Notify parent component of mode changes (hide CAT markers when this layer is visible)
    useEffect(() => {
        if (onModeChange) {
            onModeChange(visible);
        }
    }, [visible, onModeChange]);

    // Critical gap threshold - only show the most severe problems
    const CRITICAL_THRESHOLD_MBPS = 5;

    // Affordability threshold (UN standard: internet should be < 2% of income)
    const AFFORDABILITY_BURDEN_THRESHOLD = 2.0;

    // Scenario-specific cost estimation
    // TIERED COST MODEL based on actual Alaska ISP data:
    // - Tier 1 (Urban/GCI): $125/mo - Anchorage, Fairbanks, Juneau
    // - Tier 2 (Rural/FastWyre): $450/mo - Fort Yukon as reference case
    // Starlink: Flat $120/mo everywhere - potential equalizer
    const getScenarioCost = (afford: AffordabilityZone | undefined, lat: number): number => {
        if (useStarlink) {
            return 120; // Flat Starlink rate - universal pricing
        }

        // REGIONAL ISP: 2-Tier Model
        // Urban threshold: ~62°N covers Anchorage (61°N), Fairbanks (64°N is exception - has GCI)
        // We use a simple population-density proxy: areas above 63°N are rural except major cities
        // For simplicity: lat > 63 AND not near major city coordinates = Rural tier
        if (lat > 63) {
            return 450;  // Rural/FastWyre tier (Fort Yukon reference)
        }
        return 125;      // Urban/GCI tier (Anchorage, Fairbanks, Juneau)
    };

    // Calculate burden for a tile under current scenario
    const getScenarioBurden = (afford: AffordabilityZone | undefined, lat: number): number | null => {
        if (!afford || !afford.monthly_income || afford.monthly_income <= 0) {
            return null; // Cannot calculate without income data
        }
        const cost = getScenarioCost(afford, lat);
        return (cost / afford.monthly_income) * 100;
    };

    // Check if a tile has an affordability gap under current scenario
    const hasAffordabilityGap = (tile: PerformanceTile): boolean => {
        if (!tile.lat || !tile.lon) return false;
        const afford = getAffordabilityForTile(tile.lat, tile.lon);
        const burden = getScenarioBurden(afford, tile.lat);
        return burden !== null && burden >= AFFORDABILITY_BURDEN_THRESHOLD;
    };

    const visibleTiles = useMemo(() => {
        // Filter to Alaska using two-zone logic with exclusions
        const alaskaTiles = tiles.filter(t => {
            if (!t.lat || !t.lon) return false;

            // Hardcoded exclusion: BC/Yukon border region (59-61°N, 130-134°W)
            if (t.lat >= 59 && t.lat <= 61 && t.lon >= -134 && t.lon <= -130) {
                return false;
            }

            // Northern Alaska (above 60°N) - 141st meridian border
            if (t.lat > 60) {
                return t.lon >= -168 && t.lon <= -141;
            }
            // Southern Alaska / Panhandle (below 60°N) - tightened boundary
            return t.lat >= 54 && t.lon >= -168 && t.lon <= -135;
        });

        if (showGapsOnly) {
            // Gap Hunter mode: scenario-branched logic
            return alaskaTiles.filter(t => {
                const hasSpeedGap = t.avg_d_mbps !== null &&
                    t.avg_d_mbps < CRITICAL_THRESHOLD_MBPS &&
                    t.avg_d_mbps > 0.1;
                const hasAffordGap = hasAffordabilityGap(t);

                if (useStarlink) {
                    return hasAffordGap;
                } else {
                    // REGIONAL ISP SCENARIO (current reality):
                    // A gap is EITHER a speed problem OR an affordability problem
                    return hasSpeedGap || hasAffordGap;
                }
            });
        } else {
            // Exploration mode: show ONLY healthy areas (green >= 25 Mbps)
            return alaskaTiles.filter(t =>
                t.avg_d_mbps !== null &&
                t.avg_d_mbps >= TELEHEALTH_THRESHOLD_MBPS
            );
        }
    }, [tiles, showGapsOnly, useStarlink, affordabilityData]);

    // Re-render map when filter or scenario changes
    useEffect(() => {
        if (visible && tiles.length > 0) {
            renderCanvasMarkers(visibleTiles);
        }
    }, [visible, visibleTiles, zoomLevel, useStarlink, affordabilityData]);

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

    // Find nearest affordability data (nearest ZCTA within ~20km)
    function getAffordabilityForTile(lat: number, lon: number): AffordabilityZone | undefined {
        if (!affordabilityData.length) return undefined;

        let nearest: AffordabilityZone | undefined;
        let minDist = Infinity;
        const MAX_DIST_DEG = 0.2; // Approx 20km

        // Simple linear search is fast enough for ~200 zones
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

    // Fly to a gap location when clicked
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

        if (isDetailView) {
            tilesToRender.forEach(tile => {
                if (tile.lat && tile.lon) {
                    // Classify the gap type
                    const hasSpeedGap = tile.avg_d_mbps !== null &&
                        tile.avg_d_mbps < CRITICAL_THRESHOLD_MBPS &&
                        tile.avg_d_mbps > 0.1;
                    const afford = getAffordabilityForTile(tile.lat, tile.lon);
                    const scenarioCost = getScenarioCost(afford, tile.lat);
                    const burdenPct = getScenarioBurden(afford, tile.lat);
                    const hasAffordGap = burdenPct !== null && burdenPct >= AFFORDABILITY_BURDEN_THRESHOLD;

                    // Determine marker color and size based on gap type AND scenario
                    // Regional ISP: Full gap styling (red/purple/dark red)
                    // Starlink LEO: Muted styling for affordability risks (orange, smaller)
                    const isAnyGap = useStarlink
                        ? hasAffordGap  // LEO: only affordability matters
                        : (hasSpeedGap || hasAffordGap);  // Regional: both matter

                    // In "Show Gaps Only" mode, skip tiles that don't have an identifiable gap
                    if (showGapsOnly && !isAnyGap) {
                        return; // Skip this tile
                    }

                    let markerColor = tile.color;
                    let markerRadius = 5;

                    if (useStarlink) {
                        // STARLINK LEO MODE: Muted styling for residual affordability risks
                        if (hasAffordGap) {
                            markerColor = '#f97316'; // Muted orange - residual risk
                            markerRadius = 6; // Slightly smaller than full gaps
                        }
                    } else {
                        // REGIONAL ISP MODE: Full gap styling
                        if (hasSpeedGap && hasAffordGap) {
                            markerColor = '#b91c1c'; // Dark red - double jeopardy
                            markerRadius = 8;
                        } else if (hasSpeedGap) {
                            markerColor = '#ef4444'; // Red - speed gap
                            markerRadius = 8;
                        } else if (hasAffordGap) {
                            markerColor = '#a855f7'; // Purple - affordability gap
                            markerRadius = 8;
                        }
                    }

                    const marker = L.circleMarker([tile.lat, tile.lon], {
                        radius: markerRadius,
                        fillColor: markerColor,
                        fillOpacity: useStarlink ? 0.7 : 0.85, // Muted opacity for LEO
                        color: isAnyGap ? '#000' : markerColor,
                        weight: isAnyGap ? (useStarlink ? 1 : 2) : 1,
                        opacity: useStarlink ? 0.6 : 0.8,
                        renderer: canvasRenderer
                    });

                    const speedDisplay = tile.avg_d_mbps && tile.avg_d_mbps < 0.5
                        ? 'No Connection'
                        : `${tile.avg_d_mbps?.toFixed(1) ?? 'N/A'} Mbps`;

                    // Build scenario-specific values
                    const costDisplay = `$${scenarioCost}`;
                    const burdenDisplay = burdenPct !== null ? `${burdenPct.toFixed(1)}%` : 'Unavailable';
                    const ispDisplay = useStarlink ? 'Starlink (LEO)' : (afford?.isp || 'Unknown');
                    const scenarioLabel = useStarlink ? 'Universal LEO Scenario' : 'Regional Pricing (Current)';

                    // Gap type classification for popup - SCENARIO AWARE
                    let gapLabel = '✅ Service Area';
                    let gapColor = '#22c55e';

                    if (useStarlink) {
                        // LEO MODE: Different labeling
                        if (hasAffordGap) {
                            gapLabel = '⚠️ Residual Affordability Risk';
                            gapColor = '#f97316';
                        } else {
                            gapLabel = '✅ LEO Coverage Viable';
                            gapColor = '#22c55e';
                        }
                    } else {
                        // REGIONAL MODE: Standard gap labels
                        if (hasSpeedGap && hasAffordGap) {
                            gapLabel = '🚨 Double Jeopardy';
                            gapColor = '#b91c1c';
                        } else if (hasSpeedGap) {
                            gapLabel = '⚠️ Speed Gap';
                            gapColor = '#ef4444';
                        } else if (hasAffordGap) {
                            gapLabel = '💸 Affordability Gap';
                            gapColor = '#a855f7';
                        }
                    }

                    // Burden status indicator
                    const burdenStatus = burdenPct !== null
                        ? (burdenPct >= AFFORDABILITY_BURDEN_THRESHOLD
                            ? `<span style="color: #dc2626; font-weight: 600;">⚠️ ${burdenDisplay}</span>`
                            : `<span style="color: #22c55e;">✓ ${burdenDisplay}</span>`)
                        : 'Unavailable';

                    // Build scenario-aware popup content
                    const tagSection = useStarlink
                        ? (hasAffordGap
                            ? `<div style="display: flex; gap: 4px; margin-bottom: 8px;">
                                <span style="background: #fff7ed; color: #ea580c; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 500;">Cost Risk</span>
                               </div>`
                            : '')
                        : ((hasSpeedGap || hasAffordGap)
                            ? `<div style="display: flex; gap: 4px; margin-bottom: 8px;">
                                ${hasSpeedGap ? '<span style="background: #fef2f2; color: #dc2626; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 500;">Speed</span>' : ''}
                                ${hasAffordGap ? '<span style="background: #faf5ff; color: #9333ea; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 500;">Cost</span>' : ''}
                               </div>`
                            : '');

                    const leoNote = useStarlink && hasAffordGap
                        ? `<div style="font-size: 9px; color: #6b7280; margin-top: 6px; font-style: italic;">
                            Speed barrier removed by LEO, cost remains a concern.
                           </div>`
                        : '';

                    marker.bindPopup(`
                        <div style="min-width: 240px;">
                            <div style="font-weight: bold; color: ${gapColor}; margin-bottom: 6px; font-size: 13px;">
                                ${gapLabel}
                            </div>
                            
                            ${tagSection}
                            
                            <div style="font-size: 12px; line-height: 1.6;">
                                <div><strong>Actual Speed:</strong> ${speedDisplay}</div>
                                <div><strong>FCC Threshold:</strong> 25 Mbps</div>
                                <hr style="margin: 8px 0; border-color: #e5e7eb;" />
                                
                                <div style="background: #f9fafb; padding: 8px; border-radius: 4px; border-left: 3px solid ${useStarlink ? '#3b82f6' : '#7c3aed'};">
                                    <div style="font-weight: 600; font-size: 11px; color: #374151; margin-bottom: 4px;">
                                        💰 Affordability Analysis
                                        <span style="font-weight: 400; color: #6b7280; display: block; font-size: 10px;">
                                            ${scenarioLabel}
                                        </span>
                                    </div>
                                    <div><strong>Est. Cost:</strong> ${costDisplay}/mo</div>
                                    <div><strong>Cost Burden:</strong> ${burdenStatus} of income</div>
                                    ${afford ? `
                                        <div style="font-size: 10px; color: #6b7280; margin-top: 4px; border-top: 1px solid #e5e7eb; padding-top: 4px;">
                                            Provider: ${ispDisplay}<br/>
                                            ZCTA: ${afford.zcta} · Income: $${afford.median_income?.toLocaleString() || 'Unavailable'}/yr
                                        </div>
                                    ` : `
                                        <div style="font-style: italic; color: #9ca3af; font-size: 10px; margin-top: 4px;">
                                            Estimated (no local income data)
                                        </div>
                                    `}
                                </div>
                                
                                <div style="font-size: 9px; color: #6b7280; margin-top: 6px;">
                                    UN Standard: Internet < 2% of income
                                </div>
                            </div>
                        </div>
                    `);

                    layerGroup.addLayer(marker);
                }
            });
        } else {
            // Aggregated view
            const aggregated = new Map<string, { lat: number; lon: number; speeds: number[]; tests: number }>();

            tilesToRender.forEach(tile => {
                if (tile.lat && tile.lon && tile.avg_d_mbps && tile.avg_d_mbps > 0.1) {
                    const key = `${Math.round(tile.lat * 2) / 2},${Math.round(tile.lon * 2) / 2}`;
                    const existing = aggregated.get(key);
                    if (existing) {
                        existing.speeds.push(tile.avg_d_mbps);
                        existing.tests += tile.tests;
                    } else {
                        aggregated.set(key, {
                            lat: Math.round(tile.lat * 2) / 2,
                            lon: Math.round(tile.lon * 2) / 2,
                            speeds: [tile.avg_d_mbps],
                            tests: tile.tests
                        });
                    }
                }
            });

            aggregated.forEach(data => {
                const avgSpeed = data.speeds.reduce((a, b) => a + b, 0) / data.speeds.length;

                // In gap mode, use scenario-aware colors
                // LEO: muted orange (residual risk), Regional: red (gap)
                const color = showGapsOnly
                    ? (useStarlink ? '#f97316' : '#ef4444')
                    : getSpeedColor(avgSpeed);

                const marker = L.circleMarker([data.lat, data.lon], {
                    radius: Math.min(20, Math.max(8, data.speeds.length / 5)),
                    fillColor: color,
                    fillOpacity: 0.7,
                    color: '#000',
                    weight: 1,
                    opacity: 0.6,
                    renderer: canvasRenderer
                });

                // Create popup with location loading
                const popupId = `popup-${data.lat}-${data.lon}`;
                const popupContent = `
                    <div style="min-width: 160px;">
                        <div id="${popupId}-name" style="font-weight: bold; color: ${color}; margin-bottom: 4px;">
                            📍 Loading location...
                        </div>
                        <div style="font-size: 12px; line-height: 1.5;">
                            <div><strong>Avg Speed:</strong> ${avgSpeed.toFixed(1)} Mbps</div>
                            <div><strong>Coverage:</strong> ${data.speeds.length} tiles</div>
                            <div><strong>Tests:</strong> ${data.tests.toLocaleString()}</div>
                            <div style="font-size: 10px; color: #6b7280; margin-top: 4px;">
                                ${data.lat.toFixed(2)}°N, ${Math.abs(data.lon).toFixed(2)}°W
                            </div>
                        </div>
                    </div>
                `;

                marker.bindPopup(popupContent);

                // Fetch location name when popup opens
                marker.on('popupopen', async () => {
                    try {
                        const response = await fetch(
                            `http://localhost:5001/api/cat/performance/location?lat=${data.lat}&lon=${data.lon}`
                        );
                        const location = await response.json();
                        const nameEl = document.getElementById(`${popupId}-name`);
                        if (nameEl) {
                            const severity = avgSpeed < 5 ? '🔴 Critical' : avgSpeed < 10 ? '🟠 Poor' : '🟡 Moderate';
                            nameEl.innerHTML = `${severity}: ${location.name || 'Unknown Area'}`;
                        }
                    } catch (e) {
                        const nameEl = document.getElementById(`${popupId}-name`);
                        if (nameEl) nameEl.innerHTML = `⚠️ Service Gap Area`;
                    }
                });

                layerGroup.addLayer(marker);
            });
        }

        layerGroup.addTo(map);
        canvasLayerRef.current = layerGroup;
    }

    useEffect(() => {
        return () => {
            if (canvasLayerRef.current) map.removeLayer(canvasLayerRef.current);
        };
    }, [map]);

    if (!visible) return null;

    const underservedCount = tiles.filter(t =>
        t.avg_d_mbps !== null &&
        t.avg_d_mbps < TELEHEALTH_THRESHOLD_MBPS &&
        t.avg_d_mbps > 0.1
    ).length;

    return (
        <div style={panelStyle}>
            {/* Header */}
            <div style={headerStyle} onClick={onToggle}>
                <span>🎯 Gap Hunter</span>
                <span style={{ fontSize: '10px', cursor: 'pointer' }}>✕</span>
            </div>

            {/* Filter and Scenario Toggles */}
            <div style={{
                padding: '10px 12px',
                backgroundColor: showGapsOnly ? '#fef2f2' : '#f0fdf4',
                borderBottom: '1px solid #e5e7eb'
            }}>
                {/* Primary Filter: Show Gaps */}
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '12px', marginBottom: '12px' }}>
                    <input
                        type="checkbox"
                        checked={showGapsOnly}
                        onChange={(e) => setShowGapsOnly(e.target.checked)}
                        style={{ accentColor: '#dc2626', width: '16px', height: '16px' }}
                    />
                    <span style={{ fontWeight: '600', color: '#374151' }}>
                        Filter: Show Gaps Only
                    </span>
                </label>

                {/* Scenario Toggle: Regional vs Starlink */}
                <div style={{
                    backgroundColor: 'rgba(255,255,255,0.6)',
                    padding: '8px',
                    borderRadius: '6px',
                    border: '1px solid #e5e7eb'
                }}>
                    <div style={{ fontSize: '10px', fontWeight: '600', color: '#6b7280', marginBottom: '6px', textTransform: 'uppercase' }}>
                        Pricing Scenario
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                            onClick={() => setUseStarlink(false)}
                            style={{
                                flex: 1,
                                padding: '4px 8px',
                                fontSize: '10px',
                                borderRadius: '4px',
                                border: '1px solid',
                                borderColor: !useStarlink ? '#7c3aed' : '#e5e7eb',
                                backgroundColor: !useStarlink ? '#7c3aed' : '#f9fafb',
                                color: !useStarlink ? 'white' : '#4b5563',
                                cursor: 'pointer',
                                fontWeight: !useStarlink ? '600' : '400',
                                transition: 'all 0.2s'
                            }}
                        >
                            Regional ISP
                        </button>
                        <button
                            onClick={() => setUseStarlink(true)}
                            style={{
                                flex: 1,
                                padding: '4px 8px',
                                fontSize: '10px',
                                borderRadius: '4px',
                                border: '1px solid',
                                borderColor: useStarlink ? '#3b82f6' : '#e5e7eb',
                                backgroundColor: useStarlink ? '#3b82f6' : '#f9fafb',
                                color: useStarlink ? 'white' : '#4b5563',
                                cursor: 'pointer',
                                fontWeight: useStarlink ? '600' : '400',
                                transition: 'all 0.2s'
                            }}
                        >
                            Starlink LEO
                        </button>
                    </div>
                </div>

                <div style={{ fontSize: '10px', color: '#6b7280', marginTop: '8px', marginLeft: '2px' }}>
                    {showGapsOnly
                        ? (useStarlink
                            ? `${visibleTiles.length.toLocaleString()} affordability risks (cost > 2%)`
                            : `${visibleTiles.length.toLocaleString()} gaps (speed < 5 Mbps or cost > 2%)`)
                        : `${visibleTiles.length.toLocaleString()} healthy areas (≥25 Mbps)`}
                </div>
            </div>

            {/* Affordability Info Banner - Dynamic Content */}
            <div style={{
                padding: '8px 12px',
                backgroundColor: useStarlink ? '#fff7ed' : '#faf5ff',
                borderBottom: '1px solid #e5e7eb',
                fontSize: '11px',
                color: useStarlink ? '#ea580c' : '#7c3aed',
                borderLeft: `4px solid ${useStarlink ? '#f97316' : '#7c3aed'}`
            }}>
                <div style={{ fontWeight: '600', marginBottom: '2px' }}>
                    {useStarlink ? '🛰️ LEO Policy Scenario' : '💰 Regional Market Reality'}
                </div>
                <div style={{ color: '#4b5563' }}>
                    {useStarlink
                        ? 'Speed assumed solved. Flat $120/mo everywhere - 73% savings for rural.'
                        : 'GCI (Urban): $125/mo · FastWyre (Rural): $450/mo'}
                </div>
            </div>

            {loading ? (
                <div style={{ padding: '12px', fontSize: '12px', color: '#6b7280' }}>Loading...</div>
            ) : error ? (
                <div style={{ padding: '12px', fontSize: '12px', color: '#dc2626' }}>{error}</div>
            ) : summary?.has_data ? (
                <>
                    {/* Stats Row */}
                    <div style={{ padding: '12px', borderBottom: '1px solid #e5e7eb' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                            <div style={{ textAlign: 'center', padding: '8px', backgroundColor: '#fef2f2', borderRadius: '6px' }}>
                                <div style={{ fontSize: '22px', fontWeight: 'bold', color: '#dc2626' }}>
                                    {underservedCount.toLocaleString()}
                                </div>
                                <div style={{ fontSize: '9px', color: '#6b7280' }}>Gaps Found</div>
                            </div>
                            <div style={{ textAlign: 'center', padding: '8px', backgroundColor: '#fef2f2', borderRadius: '6px' }}>
                                <div style={{ fontSize: '22px', fontWeight: 'bold', color: '#dc2626' }}>
                                    {(100 - (summary.telehealth_viable_pct || 0)).toFixed(0)}%
                                </div>
                                <div style={{ fontSize: '9px', color: '#6b7280' }}>Need Fix</div>
                            </div>
                        </div>
                    </div>

                    {/* Top Priority Gaps - Clickable List */}
                    {showGapsOnly && topGaps.length > 0 && (
                        <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb', maxHeight: '200px', overflowY: 'auto' }}>
                            <div style={{ fontSize: '11px', fontWeight: '600', color: '#dc2626', marginBottom: '8px' }}>
                                🚨 Top Priority Gaps (click to zoom)
                            </div>
                            {topGaps.map((gap) => (
                                <div
                                    key={gap.quadkey}
                                    onClick={() => handleGapClick(gap.lat, gap.lon)}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between',
                                        padding: '6px 8px',
                                        marginBottom: '4px',
                                        backgroundColor: '#fff',
                                        border: '1px solid #e5e7eb',
                                        borderRadius: '6px',
                                        cursor: 'pointer',
                                        transition: 'all 0.15s ease'
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.backgroundColor = '#fef2f2';
                                        e.currentTarget.style.borderColor = '#fca5a5';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.backgroundColor = '#fff';
                                        e.currentTarget.style.borderColor = '#e5e7eb';
                                    }}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <span style={{
                                            fontSize: '10px',
                                            fontWeight: 'bold',
                                            color: '#9ca3af',
                                            minWidth: '18px'
                                        }}>
                                            #{gap.rank}
                                        </span>
                                        <div>
                                            <div style={{ fontSize: '11px', fontWeight: '600', color: '#1f2937' }}>
                                                {gap.name}
                                            </div>
                                            <div style={{ fontSize: '9px', color: '#6b7280' }}>
                                                {gap.tests} tests
                                            </div>
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <span style={{
                                            fontSize: '12px',
                                            fontWeight: 'bold',
                                            color: gap.color
                                        }}>
                                            {gap.speed_mbps < 0.5 ? 'No Conn' : `${gap.speed_mbps} Mbps`}
                                        </span>
                                        <span style={{ fontSize: '14px' }}>🔭</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Color Legend - Scenario Aware */}
                    <div style={{ padding: '10px 12px', fontSize: '11px', borderTop: '1px solid #e5e7eb' }}>
                        <div style={{ fontWeight: '600', color: '#374151', marginBottom: '8px' }}>
                            🎨 Color Key
                        </div>
                        {useStarlink ? (
                            // LEO Scenario Legend
                            <>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                                    <span style={{ color: '#f97316', fontSize: '14px' }}>⬤</span>
                                    <span>Residual Affordability Risk</span>
                                </div>
                                <div style={{ fontSize: '9px', color: '#6b7280', marginLeft: '22px', marginBottom: '8px' }}>
                                    Cost burden &gt; 2% even at $120/mo
                                </div>
                                <div style={{ fontSize: '9px', color: '#22c55e', fontStyle: 'italic' }}>
                                    ✓ Speed gaps removed by LEO assumption
                                </div>
                            </>
                        ) : (
                            // Regional ISP Legend  
                            <>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                                    <span style={{ color: '#ef4444', fontSize: '14px' }}>⬤</span>
                                    <span><strong>Speed Gap</strong> – &lt; 5 Mbps</span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                                    <span style={{ color: '#a855f7', fontSize: '14px' }}>⬤</span>
                                    <span><strong>Affordability Gap</strong> – Cost &gt; 2%</span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                                    <span style={{ color: '#b91c1c', fontSize: '14px' }}>⬤</span>
                                    <span><strong>Double Jeopardy</strong> – Both issues</span>
                                </div>
                            </>
                        )}
                    </div>
                </>
            ) : (
                <div style={{ padding: '12px', fontSize: '12px', color: '#6b7280' }}>No data available</div>
            )}

            <div style={{ padding: '6px 12px', fontSize: '9px', color: '#9ca3af', backgroundColor: '#f9fafb', borderTop: '1px solid #e5e7eb' }}>
                Ookla Q4 2024 · Zoom in for details
            </div>
        </div>
    );
}

const panelStyle: React.CSSProperties = {
    position: 'absolute',
    top: '10px',
    left: '10px',
    backgroundColor: 'white',
    borderRadius: '8px',
    boxShadow: '0 2px 12px rgba(0,0,0,0.2)',
    zIndex: 1000,
    minWidth: '240px',
    maxWidth: '300px',
    fontSize: '13px',
    overflow: 'hidden'
};

const headerStyle: React.CSSProperties = {
    padding: '10px 12px',
    backgroundColor: '#dc2626',
    color: 'white',
    fontSize: '14px',
    fontWeight: '700',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    cursor: 'pointer'
};
