import { afterEach, describe, expect, it, vi } from 'vitest';
import L from 'leaflet';
import './leafletSmoothWheelZoom';

describe('leafletSmoothWheelZoom', () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    document.body.replaceChildren();
  });

  it('uses the custom handler to produce fractional wheel zoom levels', () => {
    vi.useFakeTimers();
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => (
      window.setTimeout(() => callback(performance.now()), 16)
    ));
    vi.stubGlobal('cancelAnimationFrame', (id: number) => window.clearTimeout(id));

    const container = document.createElement('div');
    Object.defineProperties(container, {
      clientWidth: { value: 800 },
      clientHeight: { value: 600 },
      offsetWidth: { value: 800 },
      offsetHeight: { value: 600 },
    });
    container.getBoundingClientRect = () => ({
      x: 0,
      y: 0,
      top: 0,
      right: 800,
      bottom: 600,
      left: 0,
      width: 800,
      height: 600,
      toJSON: () => undefined,
    });
    document.body.appendChild(container);

    const map = L.map(container, {
      center: [64, -150],
      zoom: 5,
      minZoom: 4,
      maxZoom: 10,
      zoomControl: false,
      attributionControl: false,
      scrollWheelZoom: false,
      smoothWheelZoom: true,
      smoothSensitivity: 3,
      zoomSnap: 0,
    });

    expect(map.scrollWheelZoom.enabled()).toBe(false);
    expect(map.smoothWheelZoom.enabled()).toBe(true);

    container.dispatchEvent(new WheelEvent('wheel', {
      deltaY: -120,
      clientX: 400,
      clientY: 300,
      bubbles: true,
      cancelable: true,
    }));
    vi.advanceTimersByTime(32);

    expect(map.getZoom()).toBeGreaterThan(5);
    expect(Number.isInteger(map.getZoom())).toBe(false);

    map.remove();
  });

  it('responds strongly to high-precision trackpad pinch deltas', () => {
    vi.useFakeTimers();
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => (
      window.setTimeout(() => callback(performance.now()), 16)
    ));
    vi.stubGlobal('cancelAnimationFrame', (id: number) => window.clearTimeout(id));

    const container = document.createElement('div');
    Object.defineProperties(container, {
      clientWidth: { value: 800 },
      clientHeight: { value: 600 },
      offsetWidth: { value: 800 },
      offsetHeight: { value: 600 },
    });
    container.getBoundingClientRect = () => ({
      x: 0,
      y: 0,
      top: 0,
      right: 800,
      bottom: 600,
      left: 0,
      width: 800,
      height: 600,
      toJSON: () => undefined,
    });
    document.body.appendChild(container);

    const map = L.map(container, {
      center: [64.2, -152],
      zoom: 5,
      minZoom: 4,
      maxZoom: 10,
      zoomControl: false,
      attributionControl: false,
      scrollWheelZoom: false,
      smoothWheelZoom: true,
      smoothSensitivity: 3,
      zoomSnap: 0,
    });

    const wheelEvent = new WheelEvent('wheel', {
      deltaY: -1,
      clientX: 401,
      clientY: 301,
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    });
    let animationFrames = 0;
    let zoomEvents = 0;
    map.on('zoomanim', () => { animationFrames += 1; });
    map.on('zoom', () => { zoomEvents += 1; });

    container.dispatchEvent(wheelEvent);
    vi.advanceTimersByTime(16);

    expect(wheelEvent.defaultPrevented).toBe(true);
    expect(map.getZoom()).toBeGreaterThan(5.005);
    expect(animationFrames).toBeGreaterThan(0);
    expect(zoomEvents).toBe(0);

    vi.advanceTimersByTime(200);
    expect(zoomEvents).toBe(1);

    map.remove();
  });
});
