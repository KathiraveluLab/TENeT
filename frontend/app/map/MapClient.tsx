  "use client";
import HealthsitesLayer from "./HealthsitesLayer";
  import React, { useMemo, useState, useEffect } from "react";
  import {
    MapContainer,
    TileLayer,
    Marker,
    Popup,
    CircleMarker,
    LayersControl,
    LayerGroup, 
    useMap,
  } from "react-leaflet";
  import type { LatLngExpression, LatLngTuple } from "leaflet";
  import L from "leaflet";
  import "leaflet/dist/leaflet.css";

  const { BaseLayer, Overlay } = LayersControl;

  // Data - (types)

  export type HealthcareSiteType = "hospital" | "clinic" | "telehealth-kiosk";

  export interface HealthcareSite {
    id: string;
    name: string;
    type: HealthcareSiteType;
    location: LatLngTuple; // [lat, lng]
    patientsPerDoctor?: number;
    hasTelehealth?: boolean;
  }

  export interface InternetSite {
    id: string;
    name: string;
    provider: string;
    location: LatLngTuple;
    avgDownloadMbps: number;
    avgUploadMbps: number;
    latencyMs: number;
  }

  export interface DesertRegion {
    id: string;
    name: string;
    center: LatLngTuple;
    desertScore: number; // 0–100
    population: number;
    reason: string;
  }

  export interface AlaskaMapProps {
    healthcareSites?: HealthcareSite[];
    internetSites?: InternetSite[];
    desertRegions?: DesertRegion[];
  }

  // Default

  const defaultIcon = L.icon({
    iconUrl:
      "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
    iconRetinaUrl:
      "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
    shadowUrl:
      "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41],
  });

  L.Marker.prototype.options.icon = defaultIcon;

  //  Map helpers 

  const ALASKA_CENTER: LatLngExpression = [64.2008, -149.4937];

  const ALASKA_BOUNDS: L.LatLngBoundsExpression = [
    [51.2, -179.5], // SW
    [71.6, -129.0], // NE
  ];

  function FitToAlaskaBounds() {
    const map = useMap();

    useEffect(() => {
      map.fitBounds(ALASKA_BOUNDS, { padding: [20, 20] });
    }, [map]);

    return null;
  }

  function desertColor(score: number): string {
    if (score >= 80) return "#b91c1c"; // dark red
    if (score >= 60) return "#ef4444"; // red
    if (score >= 40) return "#f97316"; // orange
    if (score >= 20) return "#eab308"; // yellow
    return "#22c55e"; // green
  }

  // Map healthcare type → color
  function healthcareColor(type: HealthcareSiteType): string {
    switch (type) {
      case "hospital":
        return "#2563eb"; // blue
      case "clinic":
        return "#0f766e"; // teal
      case "telehealth-kiosk":
        return "#7c3aed"; // purple
      default:
        return "#2563eb";
    }
  }

  // ---------- test Data (Need to be replaced with real data) ----------

  const DEFAULT_HEALTHCARE_SITES: HealthcareSite[] = [
    {
      id: "h1",
      name: "Anchorage Regional Hospital",
      type: "hospital",
      location: [61.2176, -149.8997],
      patientsPerDoctor: 1200,
      hasTelehealth: true,
    },
    {
      id: "h2",
      name: "Bethel Community Clinic",
      type: "clinic",
      location: [60.7922, -161.7558],
      patientsPerDoctor: 2400,
      hasTelehealth: false,
    },
    {
      id: "h3",
      name: "Nome Telehealth Kiosk",
      type: "telehealth-kiosk",
      location: [64.5011, -165.4064],
      patientsPerDoctor: 5000,
      hasTelehealth: true,
    },
  ];

  const DEFAULT_INTERNET_SITES: InternetSite[] = [
    {
      id: "i1",
      name: "Anchorage ISP Node",
      provider: "Provider A",
      location: [61.2176, -149.8997],
      avgDownloadMbps: 150,
      avgUploadMbps: 30,
      latencyMs: 25,
    },
    {
      id: "i2",
      name: "Bethel Microwave Link",
      provider: "Provider B",
      location: [60.7922, -161.7558],
      avgDownloadMbps: 35,
      avgUploadMbps: 8,
      latencyMs: 60,
    },
    {
      id: "i3",
      name: "Rural Satellite Hub",
      provider: "Provider C",
      location: [64.5011, -165.4064],
      avgDownloadMbps: 20,
      avgUploadMbps: 5,
      latencyMs: 120,
    },
  ];

  const DEFAULT_DESERT_REGIONS: DesertRegion[] = [
    {
      id: "d1",
      name: "Western Alaska Cluster",
      center: [61.8, -158.0],
      desertScore: 82,
      population: 9000,
      reason: "Sparse facilities, long travel time to care.",
    },
    {
      id: "d2",
      name: "Northern Remote Villages",
      center: [68.0, -160.0],
      desertScore: 70,
      population: 3500,
      reason: "Extreme remoteness, seasonal access only.",
    },
    {
      id: "d3",
      name: "Southwest River Communities",
      center: [59.5, -162.0],
      desertScore: 55,
      population: 12000,
      reason: "Limited specialist availability.",
    },
  ];

  // Main Component

  const AlaskaMap: React.FC<AlaskaMapProps> = ({
    healthcareSites,
    internetSites,
    desertRegions,
  }) => {
    const [showHealthcare, setShowHealthcare] = useState(true);
    const [showInternet, setShowInternet] = useState(true);
    const [showDeserts, setShowDeserts] = useState(true);

    const healthData = useMemo(
      () => healthcareSites ?? DEFAULT_HEALTHCARE_SITES,
      [healthcareSites]
    );
    const internetData = useMemo(
      () => internetSites ?? DEFAULT_INTERNET_SITES,
      [internetSites]
    );
    const desertData = useMemo(
      () => desertRegions ?? DEFAULT_DESERT_REGIONS,
      [desertRegions]
    );

    return (
      <div
        style={{
          position: "relative",
          width: "100%",
          height: "100%",
          minHeight: "600px",
        }}
      >
        <div
          style={{
            position: "absolute",
            zIndex: 1000,
            top: 80,
            left: 10,
            background: "rgba(255,255,255,0.95)",
            padding: "10px 12px",
            borderRadius: 8,
            boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
            fontSize: 12,
            maxWidth: 260,
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: 6 }}>
            Telehealth Feasibility – Alaska
          </div>
          <div style={{ marginBottom: 6 }}>
            Compare <b>healthcare access</b> with <b>Internet quality</b> to spot
            telehealth opportunities.
          </div>
          <div style={{ marginTop: 4 }}>
            <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={showHealthcare}
                onChange={(e) => setShowHealthcare(e.target.checked)}
              />
              <span>Healthcare sites</span>
            </label>
            <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={showInternet}
                onChange={(e) => setShowInternet(e.target.checked)}
              />
              <span>Internet performance points</span>
            </label>
            <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={showDeserts}
                onChange={(e) => setShowDeserts(e.target.checked)}
              />
              <span>Healthcare desert regions</span>
            </label>
          </div>
          <hr style={{ margin: "8px 0" }} />
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            <span style={{ fontWeight: 600 }}>Legend</span>
            <span>● Blue – Hospitals</span>
            <span>● Teal – Clinics</span>
            <span>● Purple – Telehealth kiosks</span>
            <span>● Red/orange circles – High desert score</span>
          </div>
        </div>

        <MapContainer
          center={ALASKA_CENTER}
          zoom={4}
          minZoom={3}
          maxZoom={10}
          style={{ width: "100%", height: "100%" }}
          maxBounds={ALASKA_BOUNDS}
          maxBoundsViscosity={0.7}
          preferCanvas={true}

        >
          <FitToAlaskaBounds />
          <Overlay checked name="Live Health Facilities">
  <HealthsitesLayer />
</Overlay>


          <LayersControl position="topright">
            <BaseLayer name="Satellite View">
              <TileLayer
              attribution="&copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />
          </BaseLayer>

            <BaseLayer checked name="OpenStreetMap">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
            </BaseLayer>

            <BaseLayer name="Humanitarian">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &amp; Humanitarian'
                url="https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png"
              />
            </BaseLayer>

            {/* Healthcare sites */}
            {showHealthcare && (
              <Overlay checked name="Healthcare Sites">
                <LayerGroup>
                  {healthData.map((site) => (
                    <CircleMarker
                      key={site.id}
                      center={site.location}
                      radius={
                        site.type === "hospital"
                          ? 9
                          : site.type === "clinic"
                          ? 7
                          : 6
                      }
                      pathOptions={{
                        color: healthcareColor(site.type),
                        weight: 2,
                        fillOpacity: 0.8,
                      }}
                    >
                      <Popup>
                        <div style={{ fontSize: 12 }}>
                          <div style={{ fontWeight: 600 }}>{site.name}</div>
                          <div>Type: {site.type}</div>
                          {site.patientsPerDoctor && (
                            <div>
                              Patients / doctor: {site.patientsPerDoctor}
                            </div>
                          )}
                          <div>
                            Telehealth capability:{" "}
                            {site.hasTelehealth ? "Yes" : "No"}
                          </div>
                        </div>
                      </Popup>
                    </CircleMarker>
                  ))}
                </LayerGroup>
              </Overlay>
            )}

            {/* Internet performance points */}
            {showInternet && (
              <Overlay checked name="Internet Performance">
                <LayerGroup>
                  {internetData.map((node) => {
                    const avgSpeed =
                      (node.avgDownloadMbps + node.avgUploadMbps) / 2;
                    const radius = Math.max(4, Math.min(avgSpeed / 5, 12));
                    return (
                      <CircleMarker
                        key={node.id}
                        center={node.location}
                        radius={radius}
                        pathOptions={{
                          color:
                            avgSpeed >= 100
                              ? "#16a34a" // good
                              : avgSpeed >= 25
                              ? "#eab308" // medium
                              : "#f97316", // poor
                          fillOpacity: 0.6,
                          weight: 1.5,
                        }}
                      >
                        <Popup>
                          <div style={{ fontSize: 12 }}>
                            <div style={{ fontWeight: 600 }}>{node.name}</div>
                            <div>Provider: {node.provider}</div>
                            <div>
                              Down / Up: {node.avgDownloadMbps} /{" "}
                              {node.avgUploadMbps} Mbps
                            </div>
                            <div>Latency: {node.latencyMs} ms</div>
                          </div>
                        </Popup>
                      </CircleMarker>
                    );
                  })}
                </LayerGroup>
              </Overlay>
            )}

            {/* Healthcare desert regions */}
            {showDeserts && (
              <Overlay checked name="Healthcare Desert Regions">
                <LayerGroup>
                  {desertData.map((region) => {
                    const radius = 12 + (region.desertScore / 100) * 28; // 12–40
                    return (
                      <CircleMarker
                        key={region.id}
                        center={region.center}
                        radius={radius}
                        pathOptions={{
                          color: desertColor(region.desertScore),
                          fillOpacity: 0.25,
                          weight: 2,
                          dashArray: "4 4",
                        }}
                      >
                        <Popup>
                          <div style={{ fontSize: 12 }}>
                            <div style={{ fontWeight: 600 }}>{region.name}</div>
                            <div>
                              Desert score:{" "}
                              <b>{region.desertScore.toFixed(0)}</b> / 100
                            </div>
                            <div>Population: {region.population.toLocaleString()}</div>
                            <div style={{ marginTop: 4 }}>{region.reason}</div>
                            <hr />
                            <div style={{ fontSize: 11, opacity: 0.8 }}>
                              High desert score + good Internet here → strong
                              telehealth opportunity.
                            </div>
                          </div>
                        </Popup>
                      </CircleMarker>
                    );
                  })}
                </LayerGroup>
              </Overlay>
            )}
          </LayersControl>
        </MapContainer>
      </div>
    );
  };

  export default AlaskaMap;
