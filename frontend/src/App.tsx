import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { fetchRegions, CATRegion, RegionSummary, Season, AllTelehealthStatusResponse } from './api/catApi';
import RegionMarker from './components/RegionMarker';
import Legend from './components/Legend';
import SeasonSelector from './components/SeasonSelector';
import DataCoveragePanel from './components/DataCoveragePanel';
import PerformanceLayer from './components/PerformanceLayer';
import AffordabilityLayer, { AffordabilityLegend } from './components/AffordabilityLayer';
import Sidebar from './components/sidebar/Sidebar';
import ResearchComparisonPanel from './components/ResearchComparisonPanel';
import { usePinnedRegions } from './hooks/usePinnedRegions';
import { useRegionSummary } from './hooks/useRegionSummary';

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Alaska-specific coordinates. This framing keeps Alaska in focus and avoids
// opening with too much far-west Russia in the visible map area.
const ALASKA_CENTER: [number, number] = [62.2, -120.0];
const ALASKA_ZOOM = 4;
const STALE_DEFAULT_CENTERS: Array<[number, number]> = [
  [62.9752, -154.95117],
  [62.35, -146.75],
  [62.2, -141.8],
  [62.2, -170.8],
  [62.35, -136.5],
];

const ALASKA_BOUNDS: [[number, number], [number, number]] = [
  [51.0, -179.5],
  [72.0, -95.0]
];

type ActiveLayer = 'cat' | 'affordability' | 'gap';

function parseInitialUrlState() {
  if (typeof window === 'undefined') {
    return {
      region: null,
      season: 'year_round' as Season,
      layer: 'cat' as ActiveLayer,
      pins: [] as string[],
      center: ALASKA_CENTER,
      zoom: ALASKA_ZOOM,
    };
  }

  const params = new URLSearchParams(window.location.search);
  const seasonParam = params.get('season') as Season | null;
  const layerParam = params.get('layer') as ActiveLayer | null;
  const latParam = params.get('lat');
  const lngParam = params.get('lng');
  const zoomParam = params.get('zoom');
  const lat = latParam === null ? NaN : Number(latParam);
  const lng = lngParam === null ? NaN : Number(lngParam);
  const zoom = zoomParam === null ? NaN : Number(zoomParam);
  const hasSafeCenter = (
    Number.isFinite(lat)
    && Number.isFinite(lng)
    && lat >= ALASKA_BOUNDS[0][0]
    && lat <= ALASKA_BOUNDS[1][0]
    && lng >= ALASKA_BOUNDS[0][1]
    && lng <= ALASKA_BOUNDS[1][1]
  );
  const hasSafeZoom = Number.isFinite(zoom) && zoom >= 4 && zoom <= 18;
  const hasStaleDefaultViewport = (
    hasSafeCenter
    && hasSafeZoom
    && STALE_DEFAULT_CENTERS.some(([staleLat, staleLng]) => (
      Math.abs(lat - staleLat) < 0.0001
      && Math.abs(lng - staleLng) < 0.0001
    ))
    && zoom === ALASKA_ZOOM
  );

  return {
    region: params.get('region'),
    season: seasonParam && ['summer', 'winter', 'year_round'].includes(seasonParam)
      ? seasonParam
      : 'year_round',
    layer: layerParam && ['cat', 'affordability', 'gap'].includes(layerParam)
      ? layerParam
      : 'cat',
    pins: (params.get('pins') || '').split(',').map(pin => pin.trim()).filter(Boolean).slice(0, 3),
    center: hasSafeCenter && !hasStaleDefaultViewport ? [lat, lng] as [number, number] : ALASKA_CENTER,
    zoom: hasSafeZoom && !hasStaleDefaultViewport ? zoom : ALASKA_ZOOM,
  };
}

interface SelectionControllerProps {
  selectedRegionCode: string | null;
  regionSummaries: RegionSummary[];
  markerRefs: React.MutableRefObject<Record<string, L.Marker | L.CircleMarker>>;
}

interface MapUrlControllerProps {
  onViewportChange: (center: [number, number], zoom: number) => void;
}

interface ComparisonMapControllerProps {
  active: boolean;
}

function MapUrlController({ onViewportChange }: MapUrlControllerProps) {
  const map = useMapEvents({
    moveend: () => {
      const center = map.getCenter();
      onViewportChange([Number(center.lat.toFixed(5)), Number(center.lng.toFixed(5))], map.getZoom());
    },
    zoomend: () => {
      const center = map.getCenter();
      onViewportChange([Number(center.lat.toFixed(5)), Number(center.lng.toFixed(5))], map.getZoom());
    },
  });

  return null;
}

function ComparisonMapController({ active }: ComparisonMapControllerProps) {
  const map = useMap();

  useEffect(() => {
    if (!active) return;
    map.closePopup();
    map.panBy([0, 96], { animate: true, duration: 0.25 });
  }, [active, map]);

  return null;
}

function SelectionController({
  selectedRegionCode,
  regionSummaries,
  markerRefs,
}: SelectionControllerProps) {
  const map = useMap();

  useEffect(() => {
    if (!selectedRegionCode) return;

    const selected = regionSummaries.find(region => region.region_code === selectedRegionCode);
    if (!selected || selected.lat === null || selected.lon === null) return;

    map.flyTo([selected.lat, selected.lon], Math.max(map.getZoom(), 8), { duration: 1.1 });

    window.setTimeout(() => {
      markerRefs.current[selectedRegionCode]?.openPopup();
    }, 350);
  }, [map, markerRefs, regionSummaries, selectedRegionCode]);

  return null;
}

function App() {
  const initialUrlState = useMemo(() => parseInitialUrlState(), []);
  const [regions, setRegions] = useState<CATRegion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [season, setSeason] = useState<Season>(initialUrlState.season);
  const [performanceLayerVisible, setPerformanceLayerVisible] = useState(initialUrlState.layer === 'gap');
  const [affordabilityLayerVisible, setAffordabilityLayerVisible] = useState(initialUrlState.layer === 'affordability');
  const [gapModeActive, setGapModeActive] = useState(initialUrlState.layer === 'gap');
  const [affordabilitySummary, setAffordabilitySummary] = useState<AllTelehealthStatusResponse['summary'] | undefined>(undefined);
  const [selectedRegionCode, setSelectedRegionCode] = useState<string | null>(initialUrlState.region);
  const [detailsFocusKey, setDetailsFocusKey] = useState(0);
  const [visibleRegionCodes, setVisibleRegionCodes] = useState<string[] | null>(null);
  const [mapCenter, setMapCenter] = useState<[number, number]>(initialUrlState.center);
  const [mapZoom, setMapZoom] = useState(initialUrlState.zoom);
  const [urlNotice, setUrlNotice] = useState<string | null>(null);
  const markerRefs = useRef<Record<string, L.Marker | L.CircleMarker>>({});
  const {
    pinnedRegionCodes,
    isPinned,
    togglePinned,
    replacePinned,
    maxPinnedRegions,
  } = usePinnedRegions(initialUrlState.pins);
  const {
    regions: regionSummaries,
    loading: summaryLoading,
    error: summaryError,
  } = useRegionSummary();

  const registerMarker = useCallback((regionCode: string, marker: L.Marker | null) => {
    if (marker) {
      markerRefs.current[regionCode] = marker;
    } else {
      delete markerRefs.current[regionCode];
    }
  }, []);

  const registerAffordabilityMarker = useCallback((regionCode: string, marker: L.CircleMarker | null) => {
    if (marker) {
      markerRefs.current[regionCode] = marker;
    } else {
      delete markerRefs.current[regionCode];
    }
  }, []);

  const handleSelectRegion = useCallback((regionCode: string) => {
    setSelectedRegionCode(regionCode);
  }, []);

  const handleViewRegionDetails = useCallback((regionCode: string) => {
    setSelectedRegionCode(regionCode);
    setDetailsFocusKey(key => key + 1);
    markerRefs.current[regionCode]?.closePopup();
  }, []);

  const handleVisibleRegionsChange = useCallback((regionCodes: string[]) => {
    setVisibleRegionCodes(regionCodes);
  }, []);

  const handleViewportChange = useCallback((center: [number, number], zoom: number) => {
    setMapCenter(center);
    setMapZoom(zoom);
  }, []);

  const visibleRegionCodeSet = useMemo(
    () => visibleRegionCodes ? new Set(visibleRegionCodes) : null,
    [visibleRegionCodes],
  );

  const mapRegions = useMemo(() => {
    if (!visibleRegionCodeSet) return regions;
    return regions.filter(region => visibleRegionCodeSet.has(region.region_code));
  }, [regions, visibleRegionCodeSet]);
  const activeSidebarLayer = gapModeActive
    ? 'gap'
    : affordabilityLayerVisible
      ? 'affordability'
      : 'cat';

  useEffect(() => {
    if (summaryLoading || regionSummaries.length === 0) return;

    if (
      selectedRegionCode
      && !regionSummaries.some(region => region.region_code === selectedRegionCode)
    ) {
      setUrlNotice(`Community not found: ${selectedRegionCode}`);
      setSelectedRegionCode(null);
    }

    const validPinned = pinnedRegionCodes.filter(code => (
      regionSummaries.some(region => region.region_code === code)
    ));
    if (validPinned.length !== pinnedRegionCodes.length) {
      replacePinned(validPinned);
    }
  }, [pinnedRegionCodes, regionSummaries, replacePinned, selectedRegionCode, summaryLoading]);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const params = new URLSearchParams();
    if (selectedRegionCode) params.set('region', selectedRegionCode);
    if (activeSidebarLayer !== 'cat') params.set('layer', activeSidebarLayer);
    if (season !== 'year_round') params.set('season', season);
    if (pinnedRegionCodes.length) params.set('pins', pinnedRegionCodes.join(','));
    if (mapCenter[0] !== ALASKA_CENTER[0]) params.set('lat', mapCenter[0].toFixed(5));
    if (mapCenter[1] !== ALASKA_CENTER[1]) params.set('lng', mapCenter[1].toFixed(5));
    if (mapZoom !== ALASKA_ZOOM) params.set('zoom', String(mapZoom));

    const nextUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ''}`;
    window.history.replaceState(null, '', nextUrl);
  }, [activeSidebarLayer, mapCenter, mapZoom, pinnedRegionCodes, season, selectedRegionCode]);

  const toggleAffordabilityLayer = () => {
    if (!affordabilityLayerVisible) {
      setGapModeActive(false);
      setPerformanceLayerVisible(false);
    }
    setAffordabilityLayerVisible(!affordabilityLayerVisible);
  };

  const toggleGapMode = () => {
    if (!gapModeActive) {
      setAffordabilityLayerVisible(false);
      setPerformanceLayerVisible(true);
    } else {
      setPerformanceLayerVisible(false);
    }
    setGapModeActive(!gapModeActive);
  };

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const data = await fetchRegions(season);
        setRegions(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
        console.error('Error loading regions:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [season]);

  const getSeasonInfo = () => {
    switch (season) {
      case 'summer': return { label: 'Summer', note: 'All transport modes' };
      case 'winter': return { label: 'Winter', note: 'Limited routes' };
      case 'year_round': return { label: 'Year-Round', note: 'Average' };
    }
  };

  return (
    <div style={{ height: '100vh', width: '100%', margin: 0, padding: 0, display: 'flex', overflow: 'hidden' }}>
      <Sidebar
        regions={regionSummaries}
        loading={summaryLoading}
        error={summaryError}
        selectedRegionCode={selectedRegionCode}
        season={season}
        activeLayer={activeSidebarLayer}
        pinnedRegionCodes={pinnedRegionCodes}
        maxPinnedRegions={maxPinnedRegions}
        onSelectRegion={handleSelectRegion}
        detailsFocusKey={detailsFocusKey}
        onTogglePin={togglePinned}
        isPinned={isPinned}
        onVisibleRegionsChange={handleVisibleRegionsChange}
      />

      <div style={{ position: 'relative', flex: 1, minWidth: 0, height: '100vh' }}>
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          maxBounds={ALASKA_BOUNDS}
          maxBoundsViscosity={1.0}
          minZoom={4}
          zoomControl={true}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          />

          <SelectionController
            selectedRegionCode={selectedRegionCode}
            regionSummaries={regionSummaries}
            markerRefs={markerRefs}
          />

          <MapUrlController onViewportChange={handleViewportChange} />

          <ComparisonMapController active={pinnedRegionCodes.length >= 2} />

          {!gapModeActive && !affordabilityLayerVisible && mapRegions.map(region => (
            <RegionMarker
              key={region.region_code}
              region={region}
              selected={region.region_code === selectedRegionCode}
              onSelect={handleSelectRegion}
              onViewDetails={handleViewRegionDetails}
              onMarkerReady={registerMarker}
            />
          ))}

          <PerformanceLayer
            visible={performanceLayerVisible}
            onToggle={() => setPerformanceLayerVisible(false)}
            onModeChange={setGapModeActive}
          />

          <AffordabilityLayer
            visible={affordabilityLayerVisible}
            selectedRegionCode={selectedRegionCode}
            onSelect={handleSelectRegion}
            onViewDetails={handleViewRegionDetails}
            onMarkerReady={registerAffordabilityMarker}
            onDataLoad={setAffordabilitySummary}
          />
        </MapContainer>

      <ResearchComparisonPanel
        pinnedRegionCodes={pinnedRegionCodes}
        season={season}
        onSelectRegion={handleSelectRegion}
      />

      {loading && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 1000,
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(10px)',
          padding: '24px 48px',
          borderRadius: '12px',
          boxShadow: '0 8px 32px rgba(31, 38, 135, 0.15)',
          fontSize: '15px',
          fontWeight: '500',
          color: '#475569',
          border: '1px solid rgba(255, 255, 255, 0.3)'
        }}>
          Loading community data...
        </div>
      )}

      {error && (
        <div style={{
          position: 'absolute',
          top: '80px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 1000,
          background: 'rgba(254, 226, 226, 0.95)',
          color: '#dc2626',
          padding: '12px 24px',
          borderRadius: '8px',
          fontSize: '14px',
          fontWeight: '500'
        }}>
          {error}
        </div>
      )}

      {urlNotice && (
        <div style={{
          position: 'absolute',
          top: '128px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 1000,
          background: 'rgba(255, 251, 235, 0.96)',
          color: '#92400e',
          padding: '10px 18px',
          borderRadius: '8px',
          fontSize: '13px',
          fontWeight: '600',
          border: '1px solid #f59e0b'
        }}>
          {urlNotice}
        </div>
      )}

      {!loading && !performanceLayerVisible && !affordabilityLayerVisible && (
        <div style={{
          position: 'absolute',
          top: '20px',
          left: '60px',
          zIndex: 1000,
          display: 'flex',
          gap: '10px'
        }}>
          <button
            onClick={toggleGapMode}
            style={{
              background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              padding: '12px 20px',
              fontSize: '13px',
              fontWeight: '600',
              cursor: 'pointer',
              boxShadow: '0 4px 16px rgba(239, 68, 68, 0.3)',
              transition: 'transform 0.2s, box-shadow 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            Gap Hunter
          </button>

          <button
            onClick={toggleAffordabilityLayer}
            style={{
              background: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              padding: '12px 20px',
              fontSize: '13px',
              fontWeight: '600',
              cursor: 'pointer',
              boxShadow: '0 4px 16px rgba(245, 158, 11, 0.3)',
              transition: 'transform 0.2s, box-shadow 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            Affordability
          </button>
        </div>
      )}

      {/* RIGHT SIDE: Title + Season Dropdown */}
      <div style={{
        position: 'absolute',
        top: '20px',
        right: '20px',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-end',
        gap: '12px'
      }}>
        {/* Title Card with Dropdown */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.92)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          padding: '12px 16px',
          borderRadius: '10px',
          boxShadow: '0 4px 16px rgba(31, 38, 135, 0.1)',
          border: '1px solid rgba(255, 255, 255, 0.3)',
          display: 'flex',
          alignItems: 'center',
          gap: '16px'
        }}>
          <div>
            <div style={{
              fontSize: '15px',
              fontWeight: '700',
              color: '#0f172a',
              letterSpacing: '-0.02em'
            }}>
              TENeT
            </div>
            <div style={{
              fontSize: '10px',
              color: '#64748b'
            }}>
              Telehealth Network Tracker
            </div>
          </div>
          {/* Season Dropdown integrated in title card */}
          <SeasonSelector season={season} onChange={setSeason} />
        </div>

        {/* Close Affordability button */}
        {affordabilityLayerVisible && (
          <button
            onClick={() => setAffordabilityLayerVisible(false)}
            style={{
              background: 'rgba(55, 65, 81, 0.9)',
              backdropFilter: 'blur(10px)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              padding: '10px 16px',
              fontSize: '13px',
              fontWeight: '600',
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
            }}
          >
            ✕ Close Affordability
          </button>
        )}
      </div>

      {/* BOTTOM RIGHT: Legend */}
      {!loading && !gapModeActive && !affordabilityLayerVisible && (
        <Legend totalRegions={regions.length} />
      )}

      {/* Affordability Legend */}
      {!loading && affordabilityLayerVisible && (
        <AffordabilityLegend summary={affordabilitySummary} />
      )}

      {/* Data Coverage Panel - bottom left */}
      {!loading && !gapModeActive && !affordabilityLayerVisible && (
        <DataCoveragePanel />
      )}
      </div>
    </div>
  );
}

export default App;
