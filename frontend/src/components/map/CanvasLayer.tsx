import React from 'react';
import { useCanvasOverlay } from '../../hooks/useCanvasOverlay';
import L from 'leaflet';

export const CanvasLayer: React.FC = () => {
  useCanvasOverlay((ctx: CanvasRenderingContext2D, map: L.Map) => {
    // A mock drawing function to verify integration
    // We will draw the actual data in PR 2
    // Draw at a fixed geographic coordinate (e.g. center of Alaska)
    // so we can verify it stays perfectly pinned to the map during zoom and pan
    const fixedLocation = L.latLng(64.2008, -149.4937);
    const point = map.latLngToContainerPoint(fixedLocation);
    
    ctx.beginPath();
    ctx.arc(point.x, point.y, 50, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255, 0, 0, 0.3)';
    ctx.fill();
    ctx.strokeStyle = 'red';
    ctx.lineWidth = 2;
    ctx.stroke();
  });

  return null; // The hook injects the canvas directly into the DOM
};
