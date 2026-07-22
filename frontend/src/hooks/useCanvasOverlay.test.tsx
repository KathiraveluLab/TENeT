import { renderHook } from '@testing-library/react';
import { useCanvasOverlay } from './useCanvasOverlay';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock react-leaflet's useMap
vi.mock('react-leaflet', () => ({
  useMap: vi.fn(),
}));

describe('useCanvasOverlay', () => {
  let mockMap: any;

  beforeEach(() => {
    mockMap = {
      getPanes: vi.fn().mockReturnValue({
        overlayPane: { appendChild: vi.fn() },
      }),
      getSize: vi.fn().mockReturnValue(L.point(800, 600)),
      getBounds: vi.fn().mockReturnValue(L.latLngBounds(L.latLng(0, 0), L.latLng(10, 10))),
      latLngToLayerPoint: vi.fn().mockReturnValue(L.point(0, 0)),
      getZoomScale: vi.fn().mockReturnValue(1),
      getZoom: vi.fn().mockReturnValue(5),
      on: vi.fn(),
      off: vi.fn(),
      _latLngToNewLayerPoint: vi.fn().mockReturnValue(L.point(0, 0)),
    };
    vi.mocked(useMap).mockReturnValue(mockMap);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('injects a canvas into the map overlay pane', () => {
    const onDraw = vi.fn();
    const { result } = renderHook(() => useCanvasOverlay(onDraw));

    expect(result.current.current).toBeInstanceOf(HTMLCanvasElement);
    expect(mockMap.getPanes).toHaveBeenCalled();
    expect(mockMap.getPanes().overlayPane.appendChild).toHaveBeenCalledWith(result.current.current);
    expect(result.current.current?.classList.contains('leaflet-canvas-overlay')).toBe(true);
  });

  it('binds to map events', () => {
    const onDraw = vi.fn();
    renderHook(() => useCanvasOverlay(onDraw));

    expect(mockMap.on).toHaveBeenCalledWith('moveend', expect.any(Function));
    expect(mockMap.on).toHaveBeenCalledWith('zoomend', expect.any(Function));
    expect(mockMap.on).toHaveBeenCalledWith('resize', expect.any(Function));
    expect(mockMap.on).toHaveBeenCalledWith('zoomanim', expect.any(Function));
  });

  it('cleans up resources on unmount', () => {
    const onDraw = vi.fn();
    const { unmount } = renderHook(() => useCanvasOverlay(onDraw));

    unmount();

    expect(mockMap.off).toHaveBeenCalledWith('moveend', expect.any(Function));
    expect(mockMap.off).toHaveBeenCalledWith('zoomend', expect.any(Function));
    expect(mockMap.off).toHaveBeenCalledWith('resize', expect.any(Function));
    expect(mockMap.off).toHaveBeenCalledWith('zoomanim', expect.any(Function));
  });
});
