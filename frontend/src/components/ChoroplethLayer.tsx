/**
 * ChoroplethLayer.tsx
 * 
 * Renders Alaska Borough/Census Area boundaries as colored polygons
 * with aggregated performance data and context-rich tooltips.
 */
import { useEffect, useState, useMemo } from 'react';
import { GeoJSON } from 'react-leaflet';
import L from 'leaflet';
import type { MultiPolygon } from 'geojson';
import {
    fetchBoundaries,
    type AffordabilityZone,
    type BoundaryCollection,
    type BoundaryProperties,
    type PerformanceTile,
} from '../api/catApi';
import { errorMessage, isAbortError } from '../api/http';
import { escapeHtml } from '../utils/escapeHtml';
import { getScenarioCost, getTrafficLightStatus } from '../utils/trafficLight';
import './map/MapLayers.css';

// Aggregated stats for a region
interface RegionStats {
    avgSpeed: number | null;
    avgLatency: number | null;
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
    const [boundaries, setBoundaries] = useState<BoundaryCollection | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Fetch boundaries GeoJSON
    useEffect(() => {
        if (!visible) return;

        const controller = new AbortController();
        setLoading(true);
        setError(null);
        fetchBoundaries(controller.signal)
            .then(data => {
                setBoundaries(data);
                setLoading(false);
            })
            .catch((error: unknown) => {
                if (isAbortError(error)) return;
                setError(errorMessage(error, 'Regional boundaries are unavailable.'));
                setLoading(false);
            });

        return () => controller.abort();
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
                    avgSpeed: null,
                    avgLatency: null,
                    avgBurden: null,
                    tileCount: 0,
                    status: 'GRAY'
                });
                continue;
            }

            // Calculate averages
            const measuredSpeeds = regionTiles
                .map(tile => tile.avg_d_mbps)
                .filter((speed): speed is number => speed !== null && Number.isFinite(speed));
            const measuredLatencies = regionTiles
                .map(tile => tile.avg_lat_ms)
                .filter((latency): latency is number => latency !== null && Number.isFinite(latency));
            const avgSpeed = measuredSpeeds.length
                ? measuredSpeeds.reduce((sum, speed) => sum + speed, 0) / measuredSpeeds.length
                : null;
            const avgLatency = measuredLatencies.length
                ? measuredLatencies.reduce((sum, latency) => sum + latency, 0) / measuredLatencies.length
                : null;

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

            const status = avgSpeed === null || avgLatency === null
                ? 'GRAY'
                : getTrafficLightStatus(avgSpeed, avgLatency, avgBurden, scenarioCost);

            stats.set(name, {
                avgSpeed: avgSpeed === null ? null : Math.round(avgSpeed * 10) / 10,
                avgLatency: avgLatency === null ? null : Math.round(avgLatency),
                avgBurden: avgBurden !== null ? Math.round(avgBurden * 10) / 10 : null,
                tileCount: regionTiles.length,
                status
            });
        }

        return stats;
    }, [boundaries, tiles, affordabilityData, useStarlink]);

    const styleFeature: L.StyleFunction<BoundaryProperties> = feature => {
        const name = feature?.properties.CommunityName;
        const stats = name ? regionStats.get(name) : undefined;
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
    const onEachFeature: L.GeoJSONOptions<BoundaryProperties, MultiPolygon>['onEachFeature'] = (feature, layer) => {
        const name = feature.properties.CommunityName;
        const stats = regionStats.get(name) || {
            avgSpeed: null, avgLatency: null, avgBurden: null, tileCount: 0, status: 'GRAY' as const
        };
        const statusInfo = STATUS_INFO[stats.status];
        const color = STATUS_COLORS[stats.status];

        // Bind tooltip for hover info
        const tooltipContent = `
            <div class="region-tooltip-content" style="--tooltip-color:${color}">
                <div class="region-tooltip-title">
                    ${escapeHtml(name)}
                </div>
                <div class="region-tooltip-metrics">
                    <div>Speed: ${stats.avgSpeed === null ? 'N/A' : `${stats.avgSpeed} Mbps`}</div>
                    <div>Latency: ${stats.avgLatency === null ? 'N/A' : `${stats.avgLatency} ms`}</div>
                    <div>Burden: ${stats.avgBurden !== null ? stats.avgBurden + '%' : 'N/A'}</div>
                    <div>Data Pts: ${stats.tileCount}</div>
                </div>
                <div class="region-tooltip-status${stats.status === 'YELLOW' ? ' has-dark-text' : ''}">
                    ${escapeHtml(statusInfo.label)}
                </div>
            </div>
        `;

        if (!(layer instanceof L.Path)) return;
        layer.bindTooltip(tooltipContent, {
            sticky: true,
            direction: 'top',
            offset: [0, -10],
            className: 'region-tooltip'
        });

        layer.on({
            mouseover: (e) => {
                const target = e.target as L.Path;
                target.setStyle({
                    fillOpacity: 0.35,  // Slightly more visible on hover
                    weight: 1,
                    color: '#ffffff'
                });
                target.bringToFront();
            },
            mouseout: (e) => {
                const target = e.target as L.Path;
                target.setStyle({
                    fillOpacity: 0.2,   // Back to ghost
                    weight: 0.5,
                    color: 'rgba(255,255,255,0.6)'
                });
            }
        });
    };

    if (!visible) return null;
    if (!boundaries) {
        if (loading) return <div className="map-layer-state" role="status">Loading regional boundaries…</div>;
        if (error) return <div className="map-layer-state is-error" role="status">{error}</div>;
        return null;
    }

    return (
        <>
            <GeoJSON
                key={`choropleth-${boundaries.features.length}-${useStarlink}`}
                data={boundaries}
                style={styleFeature}
                onEachFeature={onEachFeature}
                bubblingMouseEvents={false}
            />

            {loading && (
                <div className="map-layer-state" role="status">Refreshing regional boundaries…</div>
            )}
            {error && <div className="map-layer-state is-error" role="status">{error}</div>}
        </>
    );
};

export default ChoroplethLayer;
