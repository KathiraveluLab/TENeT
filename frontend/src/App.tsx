import { useCallback, useEffect, useMemo, useState } from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import './utils/leafletSmoothWheelZoom';
import { fetchRegions, CATRegion, Season, AllTelehealthStatusResponse } from './api/catApi';
import { errorMessage, isAbortError } from './api/http';
import RegionClusters from './components/RegionClusters';
import Legend from './components/Legend';
import DataCoveragePanel from './components/DataCoveragePanel';
import PerformanceLayer from './components/PerformanceLayer';
import AffordabilityLayer, { AffordabilityLegend } from './components/AffordabilityLayer';
import Sidebar from './components/sidebar/Sidebar';
import ResearchComparisonPanel from './components/ResearchComparisonPanel';
import ScenarioPanel from './components/scenario/ScenarioPanel';
import ScenarioLayer, { ScenarioLegend } from './components/scenario/ScenarioLayer';
import { usePinnedRegions } from './hooks/usePinnedRegions';
import { useRegionSummary } from './hooks/useRegionSummary';
import { useScenarioState } from './hooks/useScenarioState';
import { useScenarioPreview } from './hooks/useScenarioPreview';
import Dashboard, { type InsightsMapLayer } from './components/dashboard/Dashboard';
import IconButton from './components/ui/IconButton';
import MapToolbar from './components/layout/MapToolbar';
import LayerSwitcher from './components/layout/LayerSwitcher';
import {
  ComparisonMapController,
  MapViewportController,
  SelectionController,
} from './components/map/MapControllers';
import {
  baseLayerForMapMode,
  CAT_MAP_MODE,
  mapModeFromLayer,
  type BaseMapLayer,
  type MapMode,
} from './domain/mapMode';
import {
  ALASKA_BOUNDS,
  parseMapUrlState,
  type ParsedMapUrlState,
} from './domain/mapUrlState';
import { useMapSelection } from './hooks/useMapSelection';
import { useMapUrlSync } from './hooks/useMapUrlSync';
import './App.css';
import './components/map/MapMarkers.css';

delete (L.Icon.Default.prototype as L.Icon.Default & { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

type ActiveView = 'map' | 'dashboard';

function App() {
  const initialUrlState = useMemo(
    () => parseMapUrlState(typeof window === 'undefined' ? '' : window.location.search),
    [],
  );
  const [activeView, setActiveView] = useState<ActiveView>('map');
  const [regions, setRegions] = useState<CATRegion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [season, setSeason] = useState<Season>(initialUrlState.season);
  const [mapMode, setMapMode] = useState<MapMode>(initialUrlState.mapMode);
  const [affordabilitySummary, setAffordabilitySummary] = useState<AllTelehealthStatusResponse['summary'] | undefined>(undefined);
  const [visibleRegionCodes, setVisibleRegionCodes] = useState<string[] | null>(null);
  const [mapCenter, setMapCenter] = useState<[number, number]>(initialUrlState.center);
  const [mapZoom, setMapZoom] = useState(initialUrlState.zoom);
  const [urlNotice, setUrlNotice] = useState<string | null>(null);
  const {
    selectedRegionCode,
    setSelectedRegionCode,
    detailsFocusKey,
    markerRefs,
    registerMarker,
    selectRegion: handleSelectRegion,
    viewRegionDetails: handleViewRegionDetails,
  } = useMapSelection(initialUrlState.selectedRegionCode);

  // ── Scenario Mode ──────────────────────────────────────────────────
  const scenarioState = useScenarioState(season, {
    active: initialUrlState.mapMode.type === 'scenario',
    ...initialUrlState.scenario,
  });
  const scenarioPreview = useScenarioPreview(
    scenarioState.mode,
    scenarioState.thresholds,
    season,
    null,
    scenarioState.setMode,
  );
  const scenarioActive = mapMode.type === 'scenario';
  const {
    pinnedRegionCodes,
    isPinned,
    togglePinned,
    replacePinned,
    maxPinnedRegions,
  } = usePinnedRegions(initialUrlState.pinnedRegionCodes);
  const {
    regions: regionSummaries,
    loading: summaryLoading,
    error: summaryError,
  } = useRegionSummary(season);
  const restoreScenarioFromUrl = scenarioState.restoreFromUrl;

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
  const activeSidebarLayer = baseLayerForMapMode(mapMode);

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
    if (!urlNotice) return;

    const timer = window.setTimeout(() => {
      setUrlNotice(null);
    }, 5000);

    return () => window.clearTimeout(timer);
  }, [urlNotice]);

  const restoreUrlState = useCallback((state: ParsedMapUrlState) => {
    setSelectedRegionCode(state.selectedRegionCode);
    setSeason(state.season);
    setMapMode(state.mapMode);
    replacePinned(state.pinnedRegionCodes);
    setMapCenter(state.center);
    setMapZoom(state.zoom);
    restoreScenarioFromUrl({
      active: state.mapMode.type === 'scenario',
      ...state.scenario,
    });
  }, [replacePinned, restoreScenarioFromUrl, setSelectedRegionCode]);

  const serializedUrlState = useMemo(() => ({
    selectedRegionCode,
    season,
    mapMode,
    pinnedRegionCodes,
    center: mapCenter,
    zoom: mapZoom,
    scenario: {
      thresholds: scenarioState.thresholds,
      preset: scenarioState.activePreset,
    },
  }), [
    mapCenter,
    mapMode,
    mapZoom,
    pinnedRegionCodes,
    scenarioState.activePreset,
    scenarioState.thresholds,
    season,
    selectedRegionCode,
  ]);
  useMapUrlSync(serializedUrlState, restoreUrlState);

  const handleLayerChange = (layer: BaseMapLayer) => {
    if (scenarioActive) scenarioState.deactivate();
    setMapMode(mapModeFromLayer(layer));
  };

  const toggleScenarioMode = () => {
    if (!scenarioActive) {
      setMapMode({ type: 'scenario' });
      scenarioState.activate();
    } else {
      setMapMode(CAT_MAP_MODE);
      scenarioState.deactivate();
    }
  };

  // Find selected region in scenario data for sidebar card
  const selectedScenarioRegion = useMemo(() => {
    if (!scenarioActive || !scenarioPreview.data || !selectedRegionCode) return undefined;
    return scenarioPreview.data.regions.find(r => r.region_code === selectedRegionCode);
  }, [scenarioActive, scenarioPreview.data, selectedRegionCode]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        setRegions([]);
        const data = await fetchRegions(season, undefined, controller.signal);
        if (controller.signal.aborted) return;
        setRegions(data);
      } catch (caught: unknown) {
        if (isAbortError(caught)) return;
        setError(errorMessage(caught, 'Failed to load data'));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    loadData();

    return () => {
      controller.abort();
    };
  }, [season]);

  const handleInsightsViewMap = (layer: InsightsMapLayer) => {
    handleLayerChange(layer);
    setActiveView('map');
  };

  const handleInsightsViewRegion = (regionCode: string) => {
    handleLayerChange('cat');
    handleViewRegionDetails(regionCode);
    setActiveView('map');
  };

  const closeInsights = () => {
    setActiveView('map');
    window.requestAnimationFrame(() => {
      document.getElementById('insights-toolbar-button')?.focus();
    });
  };

  if (activeView === 'dashboard') {
    return (
      <Dashboard
        onClose={closeInsights}
        onViewMap={handleInsightsViewMap}
        onViewRegion={handleInsightsViewRegion}
      />
    );
  }

  return (
    <div className="tenet-app">
      <Sidebar
        regions={regionSummaries}
        loading={summaryLoading}
        error={summaryError}
        selectedRegionCode={selectedRegionCode}
        season={season}
        activeLayer={activeSidebarLayer}
        pinnedRegionCodes={pinnedRegionCodes}
        maxPinnedRegions={maxPinnedRegions}
        scenarioRegion={selectedScenarioRegion}
        onSelectRegion={handleSelectRegion}
        detailsFocusKey={detailsFocusKey}
        onTogglePin={togglePinned}
        isPinned={isPinned}
        onVisibleRegionsChange={handleVisibleRegionsChange}
      />

      <main className="map-workspace">
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          maxBounds={ALASKA_BOUNDS}
          maxBoundsViscosity={1.0}
          minZoom={4}
          zoomControl={true}
          scrollWheelZoom={false}
          smoothWheelZoom={true}
          smoothSensitivity={3}
          zoomSnap={0}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
            keepBuffer={12}
            updateWhenZooming={true}
          />

          {mapMode.type === 'cat' && (
            <RegionClusters
              regions={mapRegions}
              season={season}
              selectedRegionCode={selectedRegionCode}
              onSelectRegion={handleSelectRegion}
              onViewRegionDetails={handleViewRegionDetails}
              onMarkerReady={registerMarker}
            />
          )}

          <SelectionController
            selectedRegionCode={selectedRegionCode}
            regionSummaries={regionSummaries}
            markerRefs={markerRefs}
          />

          <MapViewportController
            center={mapCenter}
            zoom={mapZoom}
            onViewportChange={handleViewportChange}
          />

          <ComparisonMapController active={pinnedRegionCodes.length >= 2} />



          <PerformanceLayer
            visible={mapMode.type === 'gapHunter'}
            onToggle={() => setMapMode(CAT_MAP_MODE)}
          />

          <AffordabilityLayer
            visible={mapMode.type === 'telehealthAccess'}
            selectedRegionCode={selectedRegionCode}
            onSelect={handleSelectRegion}
            onViewDetails={handleViewRegionDetails}
            onMarkerReady={registerMarker}
            onDataLoad={setAffordabilitySummary}
          />

          <ScenarioLayer
            data={scenarioPreview.data}
            active={scenarioActive}
            selectedRegionCode={selectedRegionCode}
            onSelect={handleSelectRegion}
            onViewDetails={handleViewRegionDetails}
            onMarkerReady={registerMarker}
          />
        </MapContainer>

        <ResearchComparisonPanel
          pinnedRegionCodes={pinnedRegionCodes}
          season={season}
          onSelectRegion={handleSelectRegion}
        />

      {loading && (
        <div className="map-state-message map-state-message--loading" role="status">
          Loading community data...
        </div>
      )}

      {error && (
        <div className="map-state-message map-state-message--error" role="alert">
          {error}
        </div>
      )}

      {urlNotice && (
        <div className="map-state-message map-state-message--notice" role="status">
          <span>{urlNotice}</span>
          <IconButton
            aria-label="Dismiss notice"
            icon="×"
            size="small"
            onClick={() => setUrlNotice(null)}
            style={{ color: 'inherit' }}
          />
        </div>
      )}

      <MapToolbar
        season={season}
        scenarioActive={scenarioActive}
        scenarioDisabled={loading}
        onSeasonChange={setSeason}
        onOpenInsights={() => setActiveView('dashboard')}
        onToggleScenario={toggleScenarioMode}
      />

      {!loading && (
        <LayerSwitcher
          activeLayer={activeSidebarLayer}
          scenarioActive={scenarioActive}
          onChange={handleLayerChange}
        />
      )}

      {scenarioActive && (
        <div className="scenario-panel-shell">
          <ScenarioPanel
            scenario={scenarioState}
            preview={scenarioPreview}
            onClose={toggleScenarioMode}
          />
        </div>
      )}

      {/* BOTTOM LEFT: Data Coverage Panel */}
      {!loading && mapMode.type === 'cat' && (
        <DataCoveragePanel />
      )}

      {/* BOTTOM RIGHT: Legend Panel */}
      {!loading && mapMode.type === 'cat' && (
        <Legend totalRegions={regions.length} />
      )}

      {/* Affordability Legend */}
      {!loading && mapMode.type === 'telehealthAccess' && (
        <AffordabilityLegend summary={affordabilitySummary} />
      )}

      {/* Scenario Legend */}
      {!loading && scenarioActive && (
        <ScenarioLegend />
      )}
      </main>
    </div>
  );
}

export default App;
