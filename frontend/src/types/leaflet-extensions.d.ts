import 'leaflet';

declare module 'leaflet' {
  interface MapOptions {
    smoothWheelZoom?: boolean | string;
    smoothSensitivity?: number;
  }
  interface Map {
    setMaxBounds(bounds: LatLngBoundsExpression | undefined | null): this;
    _container: HTMLElement;
    _stop(): void;
    _panAnim?: { stop(): void };
    _limitZoom(zoom: number): number;
    _moveStart(any3d: boolean, zoomChanged: boolean): void;
    _move(center: LatLngExpression, zoom: number): void;
    _moveEnd(zoomChanged: boolean): void;
  }
  namespace Icon {
    interface Default {
      _getIconUrl?: string;
    }
  }
}
