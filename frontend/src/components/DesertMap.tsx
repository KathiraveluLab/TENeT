import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { getColor } from "../utils/colour";
import type { FeatureCollection, Geometry } from "geojson";

type Mode = "physical" | "telehealth";

type DesertProps = {
  community: {
    name: string;
    geoid: string;
    type: "place" | "native_village";
  };
  physical_desert: number;
  telehealth_desert: number;
  physical_count: number;
  telehealth_count: number;
};

interface DesertMapProps {
  data: FeatureCollection<Geometry, DesertProps>;
  mode: Mode;
}

export default function DesertMap({ data, mode }: DesertMapProps) {
  return (
    <MapContainer
      center={[61.2, -149.9]}
      zoom={4}
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution="© OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      <GeoJSON
        data={data}
        style={(feature) => {
          if (!feature) return { fillOpacity: 0 };

          const p = feature.properties;

          // Telehealth depends on broadband state
          if (mode === "telehealth") {
            return {
              fillColor: p.broadband.color, 
              weight: 1,
              color: "#333",
              fillOpacity: 0.7,
            };
          }
          // Physical mode stays score-based
          return {
            fillColor: getColor(p.physical_desert),
            weight: 1,
            color: "#333",
            fillOpacity: 0.7,
          };
        }}
        onEachFeature={(feature, layer) => {
          const p = feature.properties;

          layer.bindPopup(`
            <strong>${p.community.name}</strong><br/><br/>

            <b>Broadband</b><br/>
            Advertised: ${(p.broadband.advertised * 100).toFixed(0)}%<br/>
            Actual: ${(p.broadband.actual * 100).toFixed(0)}%<br/>
            Gap: ${(p.broadband.gap * 100).toFixed(0)}%<br/>
            Status: <b>${p.broadband.state.replaceAll("_", " ")}</b><br/><br/>

            <b>${mode === "physical" ? "Physical" : "Telehealth"} care</b><br/>
            Desert score: ${
              mode === "physical" ? p.physical_desert : p.telehealth_desert
            }<br/>
            Providers: ${
              mode === "physical" ? p.physical_count : p.telehealth_count
            }
          `);
        }}
      />
    </MapContainer>
  );
}
