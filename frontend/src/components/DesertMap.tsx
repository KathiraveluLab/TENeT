import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import type { LatLngExpression } from "leaflet";
import "leaflet/dist/leaflet.css";
import { getColor } from "../utils/colour";

type Mode = "physical" | "telehealth";

export interface Region {
  center: {
    lat: number;
    lon: number;
  };
  physical_desert: number;
  telehealth_desert: number;
  physical_count: number;
  telehealth_count: number;
}

interface DesertMapProps {
  data: Region[];
  mode: Mode;
}

const center: LatLngExpression = [61.2, -149.9];

// optional: small jitter to avoid perfect stacking
const jitter = () => (Math.random() - 0.5) * 0.05;

export default function DesertMap({ data, mode }: DesertMapProps) {
  // 🔒 Guard: prevent rendering before data arrives
  if (!Array.isArray(data) || data.length === 0) {
    return <div style={{ padding: 20 }}>Loading map…</div>;
  }

  return (
    <MapContainer
      center={center}
      zoom={4}
      style={{ height: "calc(100vh - 100px)", width: "100%" }}
    >
      <TileLayer
        attribution="© OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {data
        // 🔒 Guard against bad coordinates
        .filter(
          (r) =>
            typeof r.center?.lat === "number" &&
            typeof r.center?.lon === "number"
        )
        .map((r, i) => {
          const score =
            mode === "physical"
              ? r.physical_desert
              : r.telehealth_desert;

          // clamp score just in case
          const safeScore = Math.max(0, Math.min(1, score));

          // radius reflects provider availability, not constant blobs
          const radius =
            mode === "physical"
              ? Math.min(10, 3 + r.physical_count)
              : Math.min(10, 3 + r.telehealth_count);

          return (
            <CircleMarker
              key={i}
              center={[
                r.center.lat + jitter(),
                r.center.lon + jitter(),
              ]}
              radius={radius}
              pathOptions={{
                stroke: false,              // 🔑 removes ugly outlines
                fillColor: getColor(safeScore),
                fillOpacity: 0.6,           // 🔑 softer blending
              }}
            >
              <Popup>
                <div style={{ minWidth: 180 }}>
                  <strong>{mode} desert score:</strong>{" "}
                  {safeScore.toFixed(2)}
                  <br />
                  <strong>Providers nearby:</strong>{" "}
                  {mode === "physical"
                    ? r.physical_count
                    : r.telehealth_count}
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
    </MapContainer>
  );
}
