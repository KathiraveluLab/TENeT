/**
 * ChoroplethLayer.tsx
 * 
 * Renders Alaska Borough/Census Area boundaries as colored polygons
 * with aggregated performance data and context-rich tooltips.
 */
import { useEffect, useState, useMemo } from 'react';
import { useMap, GeoJSON, Popup } from 'react-leaflet';
import L from 'leaflet';
import type { PerformanceTile, AffordabilityZone } from '../api/catApi';

// GeoJSON Feature type
interface BoundaryFeature {
    type: 'Feature';
    properties: {
        CommunityName: string;
        EconomicRegion: string;
        FIPS: string;
        Census_Area: 'Y' | null;
    };
    geometry: GeoJSON.MultiPolygon;
}

interface BoundaryCollection {
    type: 'FeatureCollection';
    features: BoundaryFeature[];
}

// Aggregated stats for a region
interface RegionStats {
    avgSpeed: number;
    avgLatency: number;
    avgBurden: number | null;
    tileCount: number;
    status: 'GREEN' | 'YELLOW' | 'ORANGE' | 'RED' | 'GRAY';
}

interface ChoroplethLayerProps {
    visible: boolean;
    tiles: PerformanceTile[];
    affordabilityData: AffordabilityZone[];
    useStarlink: boolean;
}

// Thresholds (matching PerformanceLayer.tsx)
const CRITICAL_LATENCY_MS = 150;
const CRITICAL_SPEED_MBPS = 5;
const AFFORDABILITY_BURDEN_THRESHOLD = 2.0;

// Get scenario cost based on latitude
const getScenarioCost = (lat: number, useStarlink: boolean): number => {
    if (useStarlink) return 120;
    return lat > 63 ? 450 : 125;
};

// Calculate burden percentage
const getBurden = (
    lat: number,
    lon: number,
    affordabilityData: AffordabilityZone[],
    useStarlink: boolean
): number | null => {
    const afford = affordabilityData.find(a =>
        a.lat != null && a.lon != null &&
        Math.abs(a.lat - lat) < 0.1 && Math.abs(a.lon - lon) < 0.1
    );
    if (!afford?.median_income) return null;
    const cost = getScenarioCost(lat, useStarlink);
    const monthlyIncome = afford.median_income / 12;
    return (cost / monthlyIncome) * 100;
};

// Traffic light status logic
const getTrafficLightStatus = (
    avgSpeed: number,
    avgLatency: number,
    avgBurden: number | null,
    scenarioCost: number
): 'GREEN' | 'YELLOW' | 'ORANGE' | 'RED' | 'GRAY' => {
    const isRuralTier = scenarioCost >= 400;

    if (avgLatency > CRITICAL_LATENCY_MS || avgSpeed < CRITICAL_SPEED_MBPS) {
        return 'RED';
    }
    if (avgBurden !== null && avgBurden > AFFORDABILITY_BURDEN_THRESHOLD) {
        return 'RED';
    }
    if (isRuralTier) {
        return 'ORANGE';
    }
    if (avgLatency > 50 && avgLatency <= CRITICAL_LATENCY_MS) {
        return 'YELLOW';
    }
    if (avgLatency <= 50 && (avgBurden === null || avgBurden <= AFFORDABILITY_BURDEN_THRESHOLD) && avgSpeed >= 25) {
        return 'GREEN';
    }
    return 'GRAY';
};

// Status colors
const STATUS_COLORS: Record<string, string> = {
    GREEN: '#22c55e',
    YELLOW: '#facc15',
    ORANGE: '#f97316',
    RED: '#ef4444',
    GRAY: '#9ca3af'
};

// Status labels and icons
const STATUS_INFO: Record<string, { label: string; icon: string; verdict: string }> = {
    GREEN: { label: 'HD Video Ready', icon: '', verdict: 'Full telehealth capability' },
    YELLOW: { label: 'Audio/Low-Res', icon: '', verdict: 'Audio calls work; video may lag' },
    ORANGE: { label: 'Expensive Infrastructure', icon: '', verdict: 'Service available but costly ($450/mo)' },
    RED: { label: 'Async Only', icon: '', verdict: 'Real-time video/audio not feasible' },
    GRAY: { label: 'Insufficient Data', icon: '', verdict: 'Cannot assess feasibility' }
};


export const ChoroplethLayer: React.FC<ChoroplethLayerProps> = ({
    visible,
    tiles,
    affordabilityData,
    useStarlink
}) => {
    const map = useMap();
    const [boundaries, setBoundaries] = useState<BoundaryCollection | null>(null);
    const [loading, setLoading] = useState(false);
    const [selectedFeature, setSelectedFeature] = useState<{
        feature: BoundaryFeature;
        stats: RegionStats;
        position: L.LatLng;
    } | null>(null);

    // Fetch boundaries GeoJSON
    useEffect(() => {
        if (!visible) return;

        setLoading(true);
        const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001/api/cat';
        fetch(`${API_BASE}/boundaries`)
            .then(res => res.json())
            .then(data => {
                console.log('Loaded boundaries:', data.features?.length, 'regions');
                setBoundaries(data);
                setLoading(false);
            })
            .catch(err => {
                console.error('Failed to load boundaries:', err);
                setLoading(false);
            });
    }, [visible]);

    // Calculate which tiles fall within each region (simplified: use bounding box)
    const regionStats = useMemo(() => {
        if (!boundaries || tiles.length === 0) return new Map<string, RegionStats>();

        const stats = new Map<string, RegionStats>();

        for (const feature of boundaries.features) {
            const name = feature.properties.CommunityName;

            // Get bounding box of region
            const coords = feature.geometry.coordinates.flat(3);
            const lons = coords.filter((_, i) => i % 2 === 0) as number[];
            const lats = coords.filter((_, i) => i % 2 === 1) as number[];

            const minLon = Math.min(...lons);
            const maxLon = Math.max(...lons);
            const minLat = Math.min(...lats);
            const maxLat = Math.max(...lats);

            // Find tiles in bounding box
            const regionTiles = tiles.filter(t =>
                t.lat >= minLat && t.lat <= maxLat &&
                t.lon >= minLon && t.lon <= maxLon
            );

            if (regionTiles.length === 0) {
                stats.set(name, {
                    avgSpeed: 0,
                    avgLatency: 0,
                    avgBurden: null,
                    tileCount: 0,
                    status: 'GRAY'
                });
                continue;
            }

            // Calculate averages
            const avgSpeed = regionTiles.reduce((sum, t) => sum + (t.avg_d_mbps || 0), 0) / regionTiles.length;
            const avgLatency = regionTiles.reduce((sum, t) => sum + (t.avg_lat_ms || 0), 0) / regionTiles.length;

            // Calculate average burden
            let totalBurden = 0;
            let burdenCount = 0;
            for (const tile of regionTiles) {
                const burden = getBurden(tile.lat, tile.lon, affordabilityData, useStarlink);
                if (burden !== null) {
                    totalBurden += burden;
                    burdenCount++;
                }
            }
            const avgBurden = burdenCount > 0 ? totalBurden / burdenCount : null;

            // Get center lat for cost calculation
            const centerLat = (minLat + maxLat) / 2;
            const scenarioCost = getScenarioCost(centerLat, useStarlink);

            const status = getTrafficLightStatus(avgSpeed, avgLatency, avgBurden, scenarioCost);

            stats.set(name, {
                avgSpeed: Math.round(avgSpeed * 10) / 10,
                avgLatency: Math.round(avgLatency),
                avgBurden: avgBurden !== null ? Math.round(avgBurden * 10) / 10 : null,
                tileCount: regionTiles.length,
                status
            });
        }

        return stats;
    }, [boundaries, tiles, affordabilityData, useStarlink]);

    // Style function for GeoJSON
    const styleFeature = (feature: any) => {
        const name = feature.properties?.CommunityName;
        const stats = regionStats.get(name);
        const color = stats ? STATUS_COLORS[stats.status] : STATUS_COLORS.GRAY;

        return {
            fillColor: color,
            fillOpacity: 0.35,
            color: '#374151',
            weight: 1,
            opacity: 0.8
        };
    };

    // Event handlers for each feature - use tooltips for hover info
    const onEachFeature = (feature: BoundaryFeature, layer: L.Layer) => {
        const name = feature.properties.CommunityName;
        const stats = regionStats.get(name) || {
            avgSpeed: 0, avgLatency: 0, avgBurden: null, tileCount: 0, status: 'GRAY' as const
        };
        const statusInfo = STATUS_INFO[stats.status];
        const color = STATUS_COLORS[stats.status];

        // Bind tooltip for hover info
        const tooltipContent = `
            <div style="min-width: 200px; font-family: system-ui, sans-serif;">
                <div style="font-weight: 600; font-size: 13px; margin-bottom: 4px; border-bottom: 2px solid ${color}; padding-bottom: 4px;">
                    ${name}
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 11px; margin-bottom: 6px;">
                    <div>Speed: ${stats.avgSpeed} Mbps</div>
                    <div>Latency: ${stats.avgLatency} ms</div>
                    <div>Burden: ${stats.avgBurden !== null ? stats.avgBurden + '%' : 'N/A'}</div>
                    <div>Data Pts: ${stats.tileCount}</div>
                </div>
                <div style="background: ${color}; color: ${stats.status === 'YELLOW' ? '#1f2937' : 'white'}; padding: 4px 8px; border-radius: 4px; text-align: center; font-size: 11px; font-weight: 600;">
                    ${statusInfo.label}
                </div>
            </div>
        `;

        (layer as L.Path).bindTooltip(tooltipContent, {
            sticky: true,
            direction: 'top',
            offset: [0, -10],
            className: 'region-tooltip'
        });

        layer.on({
            mouseover: (e) => {
                const layer = e.target;
                layer.setStyle({
                    fillOpacity: 0.6,
                    weight: 2
                });
                layer.bringToFront();
            },
            mouseout: (e) => {
                const layer = e.target;
                layer.setStyle({
                    fillOpacity: 0.35,
                    weight: 1
                });
            }
        });
    };

    if (!visible || !boundaries) return null;

    return (
        <>
            <GeoJSON
                key={`choropleth-${boundaries.features.length}-${useStarlink}`}
                data={boundaries as any}
                style={styleFeature}
                onEachFeature={onEachFeature as any}
                bubblingMouseEvents={false}
            />

            {/* Context-Rich Tooltip Popup */}
            {selectedFeature && (
                <Popup
                    position={selectedFeature.position}
                    eventHandlers={{
                        remove: () => setSelectedFeature(null)
                    }}
                >
                    <RichTooltipCard
                        name={selectedFeature.feature.properties.CommunityName}
                        region={selectedFeature.feature.properties.EconomicRegion}
                        stats={selectedFeature.stats}
                    />
                </Popup>
            )}

            {/* Loading indicator */}
            {loading && (
                <div style={{
                    position: 'absolute',
                    top: 10,
                    right: 10,
                    background: 'white',
                    padding: '8px 12px',
                    borderRadius: 4,
                    boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                    zIndex: 1000
                }}>
                    Loading regions...
                </div>
            )}
        </>
    );
};

// Rich Tooltip Card Component
interface RichTooltipCardProps {
    name: string;
    region: string;
    stats: RegionStats;
}

const RichTooltipCard: React.FC<RichTooltipCardProps> = ({ name, region, stats }) => {
    const statusInfo = STATUS_INFO[stats.status];
    const color = STATUS_COLORS[stats.status];

    return (
        <div style={{ minWidth: 280, fontFamily: 'system-ui, sans-serif' }}>
            {/* Header */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 12,
                paddingBottom: 8,
                borderBottom: `2px solid ${color}`
            }}>
                <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>📍 {name}</div>
                    <div style={{ fontSize: 11, color: '#6b7280' }}>{region}</div>
                </div>
                <div style={{
                    background: color,
                    color: stats.status === 'YELLOW' ? '#1f2937' : 'white',
                    padding: '4px 10px',
                    borderRadius: 12,
                    fontSize: 11,
                    fontWeight: 600
                }}>
                    {statusInfo.icon} {statusInfo.label}
                </div>
            </div>

            {/* Metrics Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 8,
                marginBottom: 12
            }}>
                <MetricBox
                    icon="⚡"
                    label="Speed"
                    value={`${stats.avgSpeed} Mbps`}
                    status={stats.avgSpeed >= 25 ? 'good' : stats.avgSpeed >= 5 ? 'warn' : 'bad'}
                />
                <MetricBox
                    icon="📡"
                    label="Latency"
                    value={`${stats.avgLatency} ms`}
                    status={stats.avgLatency <= 50 ? 'good' : stats.avgLatency <= 150 ? 'warn' : 'bad'}
                />
                <MetricBox
                    icon="💰"
                    label="Cost Burden"
                    value={stats.avgBurden !== null ? `${stats.avgBurden}%` : 'N/A'}
                    status={stats.avgBurden === null ? 'neutral' :
                        stats.avgBurden <= 1 ? 'good' :
                            stats.avgBurden <= 2 ? 'warn' : 'bad'}
                />
                <MetricBox
                    icon="📊"
                    label="Data Points"
                    value={`${stats.tileCount}`}
                    status="neutral"
                />
            </div>

            {/* Verdict */}
            <div style={{
                background: '#f3f4f6',
                padding: 10,
                borderRadius: 6,
                textAlign: 'center'
            }}>
                <div style={{
                    fontWeight: 600,
                    fontSize: 13,
                    color: color,
                    marginBottom: 4
                }}>
                    {stats.status === 'GREEN' && '✓ HD Video Feasible'}
                    {stats.status === 'YELLOW' && '⚠ Audio/Low-Res Recommended'}
                    {stats.status === 'ORANGE' && '💸 Expensive Infrastructure Zone'}
                    {stats.status === 'RED' && '🚫 Real-Time Video Infeasible'}
                    {stats.status === 'GRAY' && '❓ Assessment Unavailable'}
                </div>
                <div style={{ fontSize: 11, color: '#6b7280' }}>
                    {statusInfo.verdict}
                </div>
            </div>
        </div>
    );
};

// Metric Box Sub-component
interface MetricBoxProps {
    icon: string;
    label: string;
    value: string;
    status: 'good' | 'warn' | 'bad' | 'neutral';
}

const MetricBox: React.FC<MetricBoxProps> = ({ icon, label, value, status }) => {
    const bgColors = {
        good: '#dcfce7',
        warn: '#fef9c3',
        bad: '#fee2e2',
        neutral: '#f3f4f6'
    };

    return (
        <div style={{
            background: bgColors[status],
            padding: 8,
            borderRadius: 6,
            textAlign: 'center'
        }}>
            <div style={{ fontSize: 11, color: '#6b7280' }}>{icon} {label}</div>
            <div style={{ fontSize: 13, fontWeight: 600 }}>{value}</div>
        </div>
    );
};

export default ChoroplethLayer;
