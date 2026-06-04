import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
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
import { useRegionSummary } from './hooks/useRegionSummary';

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Alaska-specific coordinates
const ALASKA_CENTER: [number, number] = [62.8, -146.0];
const ALASKA_ZOOM = 5;

const ALASKA_BOUNDS: [[number, number], [number, number]] = [
  [51.0, -181.0],
  [71.5, -129.0]
];

interface SelectionControllerProps {
  selectedRegionCode: string | null;
  regionSummaries: RegionSummary[];
  markerRefs: React.MutableRefObject<Record<string, L.Marker | L.CircleMarker>>;
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
  const [regions, setRegions] = useState<CATRegion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [season, setSeason] = useState<Season>('year_round');
  const [performanceLayerVisible, setPerformanceLayerVisible] = useState(false);
  const [affordabilityLayerVisible, setAffordabilityLayerVisible] = useState(false);
  const [gapModeActive, setGapModeActive] = useState(false);
  const [affordabilitySummary, setAffordabilitySummary] = useState<AllTelehealthStatusResponse['summary'] | undefined>(undefined);
  const [selectedRegionCode, setSelectedRegionCode] = useState<string | null>(null);
  const [visibleRegionCodes, setVisibleRegionCodes] = useState<string[] | null>(null);
  const markerRefs = useRef<Record<string, L.Marker | L.CircleMarker>>({});
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

  const handleVisibleRegionsChange = useCallback((regionCodes: string[]) => {
    setVisibleRegionCodes(regionCodes);
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
        activeLayer={activeSidebarLayer}
        onSelectRegion={handleSelectRegion}
        onVisibleRegionsChange={handleVisibleRegionsChange}
      />

      <div style={{ position: 'relative', flex: 1, minWidth: 0, height: '100vh' }}>
        <MapContainer
          center={ALASKA_CENTER}
          zoom={ALASKA_ZOOM}
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

          {!gapModeActive && !affordabilityLayerVisible && mapRegions.map(region => (
            <RegionMarker
              key={region.region_code}
              region={region}
              season={season}
              selected={region.region_code === selectedRegionCode}
              onSelect={handleSelectRegion}
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
            onMarkerReady={registerAffordabilityMarker}
            onDataLoad={setAffordabilitySummary}
          />
        </MapContainer>

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
