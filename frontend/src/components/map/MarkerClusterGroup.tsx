import RawMarkerClusterGroup from 'react-leaflet-cluster';

// In Vite 8 / bundler production builds, CJS interop can wrap default exports
// as `{ default: Component }` or even `{ default: { default: Component } }`.
// This helper unwraps any nested `.default` properties until the underlying component function/class is reached.
function resolveComponent<T>(mod: unknown): T {
  let resolved: any = mod;
  while (
    resolved &&
    typeof resolved === 'object' &&
    'default' in resolved &&
    typeof resolved.default !== 'undefined'
  ) {
    resolved = resolved.default;
  }
  return resolved as T;
}

const MarkerClusterGroup = resolveComponent<typeof RawMarkerClusterGroup>(RawMarkerClusterGroup);

export default MarkerClusterGroup;
