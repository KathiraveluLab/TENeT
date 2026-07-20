import 'leaflet';

declare module 'leaflet' {
  interface MapOptions {
    smoothWheelZoom?: boolean | 'center';
    smoothSensitivity?: number;
  }

  interface Map {
    smoothWheelZoom: Handler;
  }
}
