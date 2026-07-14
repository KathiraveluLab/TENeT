import React, { useMemo } from 'react';
import MarkerClusterGroup from 'react-leaflet-cluster';
import L from 'leaflet';
import { CATRegion, Season } from '../api/catApi';
import { getDesertScorePresentation } from '../domain/metrics';
import {
  createMarkerIcon,
  getClusterMarkerSize,
  getMarkerMetadata,
  type MarkerClusterLike,
} from '../utils/markerUtils';
import RegionMarker from './RegionMarker';

interface RegionClustersProps {
  regions: CATRegion[];
  season: Season;
  selectedRegionCode?: string | null;
  onSelectRegion?: (regionCode: string) => void;
  onViewRegionDetails?: (regionCode: string) => void;
  onMarkerReady?: (regionCode: string, marker: L.Marker | null) => void;
}

// Define globally to prevent infinite loop re-renders!
const createClusterCustomIcon = function (cluster: MarkerClusterLike) {
  const pointCount = cluster.getChildCount();
  const markers = cluster.getAllChildMarkers();

  const needScores = markers
    .map(marker => getMarkerMetadata(marker).needScore)
    .filter((score): score is number => score !== undefined && Number.isFinite(score));
  const averageNeed = needScores.length
    ? needScores.reduce((sum, score) => sum + score, 0) / needScores.length
    : null;
  const clusterColor = averageNeed === null
    ? '#94a3b8'
    : getDesertScorePresentation(averageNeed).color;

  const size = getClusterMarkerSize(pointCount);
  return createMarkerIcon(clusterColor, false, size, pointCount.toString());
};

const RegionClusters: React.FC<RegionClustersProps> = ({
  regions,
  season,
  selectedRegionCode,
  onSelectRegion,
  onViewRegionDetails,
  onMarkerReady
}) => {
  // Use stable references for MarkerClusterGroup to prevent OOM loop in React StrictMode
  const polygonOptions = useMemo(() => ({ opacity: 0, fillOpacity: 0 }), []);

  return (
    <MarkerClusterGroup
      maxClusterRadius={60}
      spiderfyOnMaxZoom={true}
      disableClusteringAtZoom={8}
      chunkedLoading={true}
      polygonOptions={polygonOptions}
      showCoverageOnHover={false}
      iconCreateFunction={createClusterCustomIcon}
    >
      {regions
        .filter((r) => r.centroid_lon !== null && r.centroid_lat !== null)
        .map((region) => (
          <RegionMarker
            key={region.region_code}
            region={region}
            activeSeason={season}
            needScore={region.necessity_score}
            selected={selectedRegionCode === region.region_code}
            onSelect={onSelectRegion}
            onViewDetails={onViewRegionDetails}
            onMarkerReady={onMarkerReady}
          />
        ))}
    </MarkerClusterGroup>
  );
};

export default React.memo(RegionClusters);
