import React, { useCallback, useEffect, useState, useMemo } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import KDBush from 'kdbush';
import { useCanvasOverlay } from '../hooks/useCanvasOverlay';
import { PerformanceTile, AffordabilityZone, PerformanceFilterType } from '../api/catApi';
import { getScenarioCost, getTrafficLightStatus } from '../utils/trafficLight';
import { escapeHtml } from '../utils/escapeHtml';

interface ProcessedPerformancePoint {
    id: number;
    tile: PerformanceTile;
    projectedPoint: L.Point;
    color: string;
    radius: number;
    popupHtml: string;
}

interface PerformanceCanvasLayerProps {
    visibleTiles: PerformanceTile[];
    affordabilityData: AffordabilityZone[];
    useStarlink: boolean;
    filterMode: PerformanceFilterType;
    zoomLevel: number;
}

export const PerformanceCanvasLayer: React.FC<PerformanceCanvasLayerProps> = ({
    visibleTiles,
    affordabilityData,
    useStarlink,
    filterMode,
    zoomLevel
}) => {
    const map = useMap();
    const [hoveredPointId, setHoveredPointId] = useState<number | null>(null);

    const getScenarioBurden = useCallback((afford: AffordabilityZone | undefined, lat: number): number | null => {
        if (!afford || afford.monthly_income <= 0) return null;
        const cost = getScenarioCost(lat, useStarlink);
        return (cost / afford.monthly_income) * 100;
    }, [useStarlink]);

    const getAffordabilityForTile = useCallback((lat: number, lon: number): AffordabilityZone | undefined => {
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
    }, [affordabilityData]);

    // Process points and build KDBush index
    const { points, index } = useMemo(() => {
        const isDetailView = zoomLevel >= 8; // DETAIL_ZOOM_THRESHOLD
        const processedPoints: ProcessedPerformancePoint[] = [];

        for (let i = 0; i < visibleTiles.length; i++) {
            const tile = visibleTiles[i];
            const afford = getAffordabilityForTile(tile.lat, tile.lon);
            const scenarioCost = getScenarioCost(tile.lat, useStarlink);
            const burdenPct = getScenarioBurden(afford, tile.lat);

            let markerColor = '#ccc';
            let markerRadius = isDetailView ? 6 : Math.min(20, Math.max(4, (tile.tests / 5)));
            let capabilityLabel = "Insufficient Data";

            // --- FILTER LOGIC ---
            if (filterMode === 'affordability') {
                const isRuralTier = scenarioCost >= 400;

                if (burdenPct === null) {
                    markerColor = '#94a3b8';
                    markerRadius = 4;
                } else if (isRuralTier) {
                    if (burdenPct >= 2) {
                        markerColor = '#EF4444';
                        markerRadius = 5;
                    } else {
                        markerColor = '#f97316';
                        markerRadius = 4;
                    }
                } else {
                    if (burdenPct < 1) {
                        markerColor = '#10B981';
                        markerRadius = 3;
                    } else if (burdenPct < 2) {
                        markerColor = '#F59E0B';
                        markerRadius = 4;
                    } else {
                        markerColor = '#EF4444';
                        markerRadius = 5;
                    }
                }
            } else if (filterMode === 'latency') {
                const lat = tile.avg_lat_ms;
                if (lat === null) {
                    markerColor = '#94a3b8';
                    markerRadius = 4;
                } else if (lat < 50) {
                    markerColor = '#10B981';
                    markerRadius = 3;
                } else if (lat < 150) {
                    markerColor = '#F59E0B';
                    markerRadius = 4;
                } else {
                    markerColor = '#EF4444';
                    markerRadius = 5;
                }
            } else {
            // Calculate status once
            let status: 'RED' | 'ORANGE' | 'YELLOW' | 'GREEN' | 'GRAY' = 'GRAY';
            if (tile.avg_d_mbps !== null && tile.avg_lat_ms !== null && burdenPct !== null) {
                status = getTrafficLightStatus(tile.avg_d_mbps, tile.avg_lat_ms, burdenPct, scenarioCost);
            }

            switch (status) {
                case 'RED': markerColor = '#EF4444'; markerRadius = 5; capabilityLabel = "Async / Text Only"; break;
                case 'ORANGE': markerColor = '#f97316'; markerRadius = 4; capabilityLabel = "Expensive Infrastructure"; break;
                case 'YELLOW': markerColor = '#F59E0B'; markerRadius = 4; capabilityLabel = "Audio / Low-Res Video"; break;
                case 'GREEN': markerColor = '#10B981'; markerRadius = 3; capabilityLabel = "HD Video Ready"; break;
                default: markerColor = '#94a3b8'; markerRadius = 4; capabilityLabel = "Insufficient Data";
            }
        }

        const projectedPoint = L.CRS.EPSG3857.latLngToPoint(L.latLng(tile.lat, tile.lon), 0);

        const latencyDisplay = tile.avg_lat_ms !== null ? `${tile.avg_lat_ms.toFixed(0)} ms` : 'N/A';
        const costDisplay = burdenPct !== null ? `${burdenPct.toFixed(1)}%` : 'N/A';
        const speedDisplay = tile.avg_d_mbps !== null ? `${tile.avg_d_mbps.toFixed(1)} Mbps` : 'N/A';

            const popupHtml = `
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
            `;

            processedPoints.push({
                id: i,
                tile,
                projectedPoint,
                color: markerColor,
                radius: markerRadius,
                popupHtml,
            });
        }

        const kdbushIndex = new KDBush(processedPoints.length);
        for (const p of processedPoints) {
            kdbushIndex.add(p.projectedPoint.x, p.projectedPoint.y);
        }
        kdbushIndex.finish();

        return { points: processedPoints, index: kdbushIndex };
    }, [visibleTiles, zoomLevel, useStarlink, filterMode, getAffordabilityForTile, getScenarioBurden]);

    const onDraw = useCallback((ctx: CanvasRenderingContext2D, mapInstance: L.Map) => {
        if (points.length === 0) return;

        const bounds = mapInstance.getBounds();
        const minPoint = L.CRS.EPSG3857.latLngToPoint(bounds.getNorthWest(), 0);
        const maxPoint = L.CRS.EPSG3857.latLngToPoint(bounds.getSouthEast(), 0);

        // Ensure bounds are correctly ordered for range query
        const minX = Math.min(minPoint.x, maxPoint.x);
        const maxX = Math.max(minPoint.x, maxPoint.x);
        const minY = Math.min(minPoint.y, maxPoint.y);
        const maxY = Math.max(minPoint.y, maxPoint.y);

        const visibleIds = index.range(minX, minY, maxX, maxY);

        const currentZoom = mapInstance.getZoom();
        const scale = mapInstance.getZoomScale(currentZoom, 0);
        const pixelBoundsMin = mapInstance.getPixelBounds().min!;

        for (const id of visibleIds) {
            const pointData = points[id];
            const px = pointData.projectedPoint.x * scale - pixelBoundsMin.x;
            const py = pointData.projectedPoint.y * scale - pixelBoundsMin.y;
            const isHovered = hoveredPointId === pointData.id;

            ctx.beginPath();
            ctx.arc(px, py, isHovered ? pointData.radius + 2 : pointData.radius, 0, Math.PI * 2);
            ctx.fillStyle = pointData.color;
            ctx.globalAlpha = 0.65;
            ctx.fill();

            ctx.globalAlpha = 1.0;
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.95)';
            ctx.lineWidth = isHovered ? 2 : 1;
            ctx.stroke();
        }
    }, [points, index, hoveredPointId]);

    // Handle hover
    useEffect(() => {
        if (!map) return;

        const popup = L.popup({ closeButton: false });
        let currentHoveredId: number | null = null;

        const handleMouseMove = (e: L.LeafletMouseEvent) => {
            const clickPt = L.CRS.EPSG3857.latLngToPoint(e.latlng, 0);
            const scale = Math.pow(2, map.getZoom());
            const searchRadius = 10 / scale; // 10 pixels

            const nearbyIds = index.within(clickPt.x, clickPt.y, searchRadius);

            let closestId = -1;
            let minDistSq = Infinity;

            for (const id of nearbyIds) {
                const pt = points[id].projectedPoint;
                const dx = pt.x - clickPt.x;
                const dy = pt.y - clickPt.y;
                const distSq = dx * dx + dy * dy;

                if (distSq < minDistSq) {
                    minDistSq = distSq;
                    closestId = id;
                }
            }

            if (closestId >= 0) {
                map.getContainer().style.cursor = 'pointer';
                if (currentHoveredId !== closestId) {
                    currentHoveredId = closestId;
                    setHoveredPointId(closestId);

                    const point = points[closestId];
                    popup.setLatLng([point.tile.lat, point.tile.lon])
                        .setContent(point.popupHtml)
                        .openOn(map);
                }
            } else {
                map.getContainer().style.cursor = '';
                if (currentHoveredId !== null) {
                    currentHoveredId = null;
                    setHoveredPointId(null);
                    map.closePopup(popup);
                }
            }
        };

        map.on('mousemove', handleMouseMove);
        return () => {
            map.off('mousemove', handleMouseMove);
            map.getContainer().style.cursor = '';
            map.closePopup(popup);
        };
    }, [map, index, points]);

    useCanvasOverlay(onDraw);

    return null;
};
