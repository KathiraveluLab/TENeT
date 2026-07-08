import React, { useMemo } from 'react';
import MarkerClusterGroup from 'react-leaflet-cluster';
import L from 'leaflet';
import { CATRegion, Season, getNeedColor } from '../api/catApi';
import RegionMarker from './RegionMarker';

interface RegionClustersProps {
  regions: CATRegion[];
  season: Season;
  selectedRegionCode?: string | null;
  onSelectRegion?: (regionCode: string) => void;
  onViewRegionDetails?: (regionCode: string) => void;
  onMarkerReady?: (regionCode: string, marker: L.Marker | null) => void;
}

// Minimal CSS for hover states
const customCSS = `
  .healthsites-cluster-wrapper {
    transition: transform 0.15s ease-out;
  }
  .healthsites-cluster-wrapper:hover {
    transform: scale(1.15) !important;
    z-index: 1000 !important;
  }
  .custom-css-marker {
    background: transparent;
    border: none;
  }
`;

if (typeof document !== 'undefined') {
  const styleId = 'healthsites-custom-css';
  if (!document.getElementById(styleId)) {
    const style = document.createElement('style');
    style.id = styleId;
    style.innerHTML = customCSS;
    document.head.appendChild(style);
  }
}

import { createMarkerIcon } from '../utils/markerUtils';

// Define globally to prevent infinite loop re-renders!
const createClusterCustomIcon = function (cluster: any) {
  const pointCount = cluster.getChildCount();
  const markers = cluster.getAllChildMarkers();

  // calculate average need score for the cluster
  let sumNeed = 0;
  markers.forEach((marker: any) => {
    sumNeed += marker.options.needScore || 0;
  });

  const avgNeed = sumNeed / pointCount;
  const clusterColor = getNeedColor(avgNeed);

  let scale = 1.0;
  if (pointCount >= 200) scale = 1.5;
  else if (pointCount >= 50) scale = 1.35;
  else if (pointCount >= 10) scale = 1.2;

  const size = 24 * scale;
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
      maxClusterRadius={25}
      spiderfyOnMaxZoom={true}
      disableClusteringAtZoom={8}
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
