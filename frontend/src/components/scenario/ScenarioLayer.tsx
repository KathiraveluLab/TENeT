/**
 * ScenarioLayer – renders scenario-colored markers on the map.
 *
 * When scenario mode is active, this layer replaces the baseline CAT markers
 * with scenario-colored markers that match the CAT layer marker styling.
 * Clicking updates selectedRegionCode.
 */
import React, { memo } from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import type { ScenarioPreviewResponse, ScenarioRegion } from '../../types/scenario';
import { getScenarioDeltaColor } from '../../types/scenario';
import {
    getTelehealthStatusColor,
    getTelehealthStatusLabel,
    getTelehealthStatusTone,
    isScenarioTelehealthStatus,
    SCENARIO_TELEHEALTH_STATUSES,
    type ScenarioTelehealthStatusName,
} from '../../domain/statusPresentation';
import {
    createMarkerIcon,
    getClusterMarkerSize,
    getMarkerMetadata,
    setMarkerMetadata,
    type MarkerClusterLike,
} from '../../utils/markerUtils';
import MarkerClusterGroup from 'react-leaflet-cluster';
import Button from '../ui/Button';
import StatusBadge from '../ui/StatusBadge';
import '../MapModeLegends.css';
import './ScenarioLayer.css';

interface ScenarioLayerProps {
    data: ScenarioPreviewResponse | null;
    active: boolean;
    selectedRegionCode: string | null;
    onSelect: (regionCode: string) => void;
    onViewDetails: (regionCode: string) => void;
    onMarkerReady?: (regionCode: string, marker: L.Marker | null) => void;
}

function deltaSymbol(delta: string): string {
    switch (delta) {
        case 'improved': return '▲';
        case 'worsened': return '▼';
        default: return '—';
    }
}

interface ScenarioMarkerProps {
    region: ScenarioRegion;
    selected: boolean;
    onSelect: (regionCode: string) => void;
    onViewDetails: (regionCode: string) => void;
    onMarkerReady?: (regionCode: string, marker: L.Marker | null) => void;
}

const ScenarioMarker = memo(function ScenarioMarker({
    region,
    selected,
    onSelect,
    onViewDetails,
    onMarkerReady,
}: ScenarioMarkerProps) {
    if (region.lat === null || region.lon === null) return null;

    const color = getTelehealthStatusColor(region.scenario_status, 'scenario');
    return (
        <Marker
            position={[region.lat, region.lon]}
            alt={`${region.name} scenario marker`}
            title={region.name}
            icon={createMarkerIcon(color, selected)}
            eventHandlers={{
                click: () => onSelect(region.region_code),
            }}
            ref={(marker) => {
                if (marker) {
                    setMarkerMetadata(marker, { scenarioStatus: region.scenario_status });
                }
                onMarkerReady?.(region.region_code, marker);
            }}
        >
            <Popup maxWidth={280}>
                <div className="scenario-popup">
                    <div className="scenario-popup__title">
                        {region.name}
                    </div>

                    <div className="scenario-popup__grid">
                        <span className="scenario-popup__label">Baseline Status</span>
                        <StatusBadge tone={getTelehealthStatusTone(region.baseline_status)}>
                            {getTelehealthStatusLabel(region.baseline_status)}
                        </StatusBadge>

                        <span className="scenario-popup__label">Scenario Status</span>
                        <StatusBadge tone={getTelehealthStatusTone(region.scenario_status)}>
                            {getTelehealthStatusLabel(region.scenario_status)}
                        </StatusBadge>

                        {region.changed && (
                            <>
                                <span className="scenario-popup__label">Change</span>
                                <strong style={{ color: getScenarioDeltaColor(region.status_delta) }}>
                                    {deltaSymbol(region.status_delta)} {region.status_delta}
                                </strong>
                            </>
                        )}

                        <span className="scenario-popup__label">Healthcare Need</span>
                        <strong>
                            {Number.isFinite(region.healthcare_need_score)
                                ? region.healthcare_need_score
                                : 'Data unavailable'}
                        </strong>
                    </div>

                    <div className="scenario-popup__disclaimer">
                        This scenario result is modeled from selected thresholds
                        and should not be interpreted as observed field data.
                    </div>

                    <Button
                        size="small"
                        variant="secondary"
                        onClick={() => onViewDetails(region.region_code)}
                        className="scenario-popup__button"
                    >
                        View Details →
                    </Button>
                </div>
            </Popup>
        </Marker>
    );
});

// Custom cluster icon for Scenario mode
const createScenarioClusterIcon = function (cluster: MarkerClusterLike) {
  const pointCount = cluster.getChildCount();
  const markers = cluster.getAllChildMarkers();

  // Find the most frequent scenario status in the cluster
  const statusCounts: Partial<Record<ScenarioTelehealthStatusName, number>> = {};
  markers.forEach(marker => {
    const candidate: unknown = getMarkerMetadata(marker).scenarioStatus;
    const status = isScenarioTelehealthStatus(candidate) ? candidate : 'DATA_UNAVAILABLE';
    statusCounts[status] = (statusCounts[status] ?? 0) + 1;
  });

  let dominantStatus: ScenarioTelehealthStatusName = 'DATA_UNAVAILABLE';
  let maxCount = 0;
  SCENARIO_TELEHEALTH_STATUSES.forEach(status => {
    const count = statusCounts[status] ?? 0;
    if (count > maxCount) {
      dominantStatus = status;
      maxCount = count;
    }
  });

  const clusterColor = getTelehealthStatusColor(dominantStatus, 'scenario');

  const size = getClusterMarkerSize(pointCount);
  return createMarkerIcon(clusterColor, false, size, pointCount.toString());
};

export default function ScenarioLayer({
    data,
    active,
    selectedRegionCode,
    onSelect,
    onViewDetails,
    onMarkerReady,
}: ScenarioLayerProps) {
    const polygonOptions = React.useMemo(() => ({ opacity: 0, fillOpacity: 0 }), []);

    if (!active || !data) return null;

    return (
        <MarkerClusterGroup
            maxClusterRadius={60}
            disableClusteringAtZoom={8}
            chunkedLoading={true}
            polygonOptions={polygonOptions}
            iconCreateFunction={createScenarioClusterIcon}
        >
            {data.regions.map(region => (
                <ScenarioMarker
                    key={region.region_code}
                    region={region}
                    selected={region.region_code === selectedRegionCode}
                    onSelect={onSelect}
                    onViewDetails={onViewDetails}
                    onMarkerReady={onMarkerReady}
                />
            ))}
        </MarkerClusterGroup>
    );
}

/* ─── Scenario Sidebar Card ────────────────────────────────────────────── */

interface ScenarioSidebarCardProps {
    region: ScenarioRegion | undefined;
}

export function ScenarioSidebarCard({ region }: ScenarioSidebarCardProps) {
    if (!region) return null;

    return (
        <section className="scenario-sidebar-card">
            <div className="scenario-sidebar-card__header">
                <span className="scenario-sidebar-card__title">
                    Scenario Estimate
                </span>
                <span className="scenario-modeled-badge">
                    MODELED
                </span>
            </div>

            <div className="scenario-sidebar-card__grid">
                <span className="scenario-sidebar-card__label">Baseline Status</span>
                <strong style={{ color: getTelehealthStatusColor(region.baseline_status) }}>
                    {getTelehealthStatusLabel(region.baseline_status)}
                </strong>

                <span className="scenario-sidebar-card__label">Scenario Status</span>
                <strong style={{ color: getTelehealthStatusColor(region.scenario_status, 'scenario') }}>
                    {getTelehealthStatusLabel(region.scenario_status)}
                </strong>

                <span className="scenario-sidebar-card__label">Healthcare Need</span>
                <strong style={{ color: '#475569' }}>
                    {Number.isFinite(region.healthcare_need_score)
                        ? region.healthcare_need_score
                        : 'Data unavailable'}
                </strong>
            </div>

            {/* Reason codes */}
            {region.reason_codes.length > 0 && (
                <div className="scenario-sidebar-card__reasons">
                    {region.reason_codes.map(code => (
                        <span
                            key={code}
                            className="scenario-sidebar-card__reason"
                        >
                            {code}
                        </span>
                    ))}
                </div>
            )}

            {region.explanation && (
                <div className="scenario-sidebar-card__explanation">
                    {region.explanation}
                </div>
            )}
        </section>
    );
}

/* ─── Scenario Legend ──────────────────────────────────────────────────── */

export function ScenarioLegend() {
    const statusItems = SCENARIO_TELEHEALTH_STATUSES.map(status => ({
        status,
        label: getTelehealthStatusLabel(status),
    }));

    return (
        <div className="scenario-legend">
            <div className="scenario-legend__title">
                What-If Scenario
                <span className="scenario-modeled-badge">
                    MODELED
                </span>
            </div>

            <div className="scenario-legend__items">
                {statusItems.map(item => (
                    <div
                        key={item.status}
                        className="scenario-legend__item"
                    >
                        <span
                            className="scenario-legend__swatch"
                            style={{ backgroundColor: getTelehealthStatusColor(item.status, 'scenario') }}
                        />
                        <span className="scenario-legend__label">
                            {item.label}
                        </span>
                    </div>
                ))}
            </div>

            <div className="scenario-legend__note">
                Scenario colors represent modeled telehealth readiness under the selected thresholds.
                Baseline data remains unchanged.
            </div>
        </div>
    );
}
