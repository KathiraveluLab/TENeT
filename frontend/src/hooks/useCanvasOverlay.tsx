import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";

export function useCanvasOverlay(
  onDraw: (ctx: CanvasRenderingContext2D, map: L.Map) => void,
) {
  const map = useMap();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const onDrawRef = useRef(onDraw);
  const redrawRef = useRef<() => void>();
  const topLeftLatLngRef = useRef<L.LatLng | null>(null);
  const initialZoomRef = useRef<number>(0);

  // Keep the ref updated to avoid re-binding events on every render, and trigger redraw if onDraw changes
  useEffect(() => {
    onDrawRef.current = onDraw;
    redrawRef.current?.();
  }, [onDraw]);

  useEffect(() => {
    // 1. Create the canvas element
    const canvas = L.DomUtil.create(
      "canvas",
      "leaflet-canvas-overlay",
    ) as HTMLCanvasElement;
    canvasRef.current = canvas;

    // Inject into overlay pane
    const pane = map.getPanes().overlayPane;
    if (!pane) return;
    pane.appendChild(canvas);

    // Apply base styles
    canvas.style.position = "absolute";
    canvas.style.top = "0";
    canvas.style.left = "0";
    canvas.style.pointerEvents = "none"; // Let clicks pass through to the map if not explicitly handled
    canvas.style.transformOrigin = "0 0";

    // We will manually manage the CSS transition property during zoom events
    // instead of using 'leaflet-zoom-animated', to perfectly support both
    // continuous wheel zoom (no transition) and native double-click zoom (0.25s transition).

    const ctx = canvas.getContext("2d");

    const redraw = () => {
      if (!ctx || !canvasRef.current) return;

      const size = map.getSize();
      const bounds = map.getBounds();
      const topLeft = bounds.getNorthWest();
      topLeftLatLngRef.current = topLeft;
      initialZoomRef.current = map.getZoom();
      const topLeftPoint = map.latLngToLayerPoint(topLeft);

      // Handle high-DPI scaling
      const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;

      canvas.width = size.x * dpr;
      canvas.height = size.y * dpr;

      canvas.style.width = `${size.x}px`;
      canvas.style.height = `${size.y}px`;

      // Position the canvas precisely over the current view
      L.DomUtil.setPosition(canvas, topLeftPoint);

      // Disable any transitions before snapping the canvas back to scale 1
      canvas.style.transition = "none";
      canvas.style.transform = `translate3d(${topLeftPoint.x}px, ${topLeftPoint.y}px, 0px) scale(1)`;

      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, size.x, size.y);

      // Call the user provided draw function
      onDrawRef.current(ctx, map);

      ctx.restore();
    };

    const handleZoomAnim = (e: any) => {
      if (!canvasRef.current || !topLeftLatLngRef.current) return;

      // Calculate scaling for smooth zoom relative to the zoom level when we last drew the canvas.
      // We CANNOT use map.getZoom() here because the smoothWheelZoom plugin continuously modifies it during the animation.
      const scale = map.getZoomScale(e.zoom, initialZoomRef.current);

      // Use internal Leaflet method to calculate the new offset of our cached bounds
      // Need to cast to any since _latLngToNewLayerPoint is marked private/internal in types
      const mapAny = map as any;
      if (typeof mapAny._latLngToNewLayerPoint !== "function") return;
      const offset = mapAny._latLngToNewLayerPoint(
        topLeftLatLngRef.current,
        e.zoom,
        e.center,
      );

      // Determine if this is a continuous wheel zoom (from our plugin) or a native Leaflet zoom
      if (e.noUpdate) {
        // Continuous requestAnimationFrame zoom -> disable CSS transition to prevent jitter
        canvasRef.current.style.transition = "none";
      } else {
        // Native zoom (double click or zoom controls) -> apply Leaflet's standard zoom transition
        canvasRef.current.style.transition =
          "transform 0.25s cubic-bezier(0,0,0.25,1)";
      }

      // Apply CSS transform to the canvas for GPU-accelerated scaling
      L.DomUtil.setTransform(canvasRef.current, offset, scale);
    };

    // 2. Bind events
    map.on("moveend", redraw);
    map.on("zoomend", redraw);
    map.on("resize", redraw);
    map.on("zoomanim", handleZoomAnim);

    // Initial draw
    redraw();
    redrawRef.current = redraw;

    return () => {
      // Cleanup
      map.off("moveend", redraw);
      map.off("zoomend", redraw);
      map.off("resize", redraw);
      map.off("zoomanim", handleZoomAnim);

      if (canvasRef.current) {
        canvasRef.current.remove();
      }
      canvasRef.current = null;
      redrawRef.current = undefined;
    };
  }, [map]);

  return canvasRef;
}
