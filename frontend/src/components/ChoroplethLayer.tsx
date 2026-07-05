/**
 * ChoroplethLayer.tsx
 * 
 * Renders Alaska Borough/Census Area boundaries as colored polygons
 * with aggregated performance data and context-rich tooltips.
 */
import { useEffect, useState, useMemo } from 'react';
import { useMap, GeoJSON } from 'react-leaflet';
import L from 'leaflet';
import type { PerformanceTile, AffordabilityZone } from '../api/catApi';
import { getScenarioCost, getTrafficLightStatus } from '../utils/trafficLight';

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

// Get burden percentage for a tile location
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

// Traffic light status colours and metadata
const STATUS_COLORS: Record<string, string> = {
    GREEN: '#10b981',   // Emerald - crisp and sharp
    YELLOW: '#f59e0b',  // Amber - pops against gray
    ORANGE: '#f97316',  // Orange
    RED: '#f43f5e',     // Rose - distinct from amber
    GRAY: '#94a3b8'     // Slate gray
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

    // Fetch boundaries GeoJSON
    useEffect(() => {
        if (!visible) return;

        setLoading(true);
        const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/cat';
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

    const styleFeature = (feature: any) => {
        const name = feature.properties?.CommunityName;
        const stats = regionStats.get(name);
        const color = stats ? STATUS_COLORS[stats.status] : STATUS_COLORS.GRAY;

        return {
            fillColor: color,
            fillOpacity: 0.2,
            color: 'rgba(255,255,255,0.6)',
            weight: 0.5,
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
                    fillOpacity: 0.35,  // Slightly more visible on hover
                    weight: 1,
                    color: '#ffffff'
                });
                layer.bringToFront();
            },
            mouseout: (e) => {
                const layer = e.target;
                layer.setStyle({
                    fillOpacity: 0.2,   // Back to ghost
                    weight: 0.5,
                    color: 'rgba(255,255,255,0.6)'
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

export default ChoroplethLayer;
