"use client";

import React from "react";
import { GeoJSON } from "react-leaflet";
import type { FeatureCollection } from "geojson";
import L from "leaflet";

const ALASKA_BBOX = [-179.5, 51.2, -129.0, 71.6]; 

export default function HealthsitesLayer() {
  const [data, setData] = React.useState<FeatureCollection | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const apiKey = process.env.NEXT_PUBLIC_HEALTHSITES_API_KEY;

    if (!apiKey) {
      setError("Missing Healthsites API key");
      setLoading(false);
      return;
    }

    const fetchAllPages = async () => {
      try {
        let allFeatures: any[] = [];
        let page = 1;
        let more = true;

        while (more && page <= 5) {
          const url = new URL("https://healthsites.io/api/v3/facilities/");
          url.searchParams.set("api-key", apiKey);
          url.searchParams.set("page", String(page));
          url.searchParams.set("extent", ALASKA_BBOX.join(","));
          url.searchParams.set("output", "geojson");

          const res = await fetch(url.toString());

          if (!res.ok) {
            throw new Error(`Healthsites API error: ${res.status}`);
          }

          const geojson: FeatureCollection = await res.json();

          if (!geojson.features || geojson.features.length === 0) {
            more = false;
            break;
          }

          allFeatures.push(...geojson.features);
          page++;
        }

        setData({
          type: "FeatureCollection",
          features: allFeatures,
        });
      } catch (err: any) {
        console.error(err);
        setError("Failed to load Healthsites data");
      } finally {
        setLoading(false);
      }
    };

    fetchAllPages();
  }, []);

  if (loading) return null;
  if (error) {
    console.error("Healthsites:", error);
    return null;
  }
  if (!data) return null;

  return (
    <GeoJSON
      data={data}
      pointToLayer={(_, latlng) =>
        L.circleMarker(latlng, {
          radius: 5,
          color: "#2563eb",
          weight: 1.8,
          fillOpacity: 0.85,
        })
      }
      onEachFeature={(feature, layer) => {
        const props: any = feature.properties || {};

        const name = props.name || "Unnamed Facility";
        const type = props.facility_type || props.type || "Unknown";
        const operator = props.operator || "N/A";
        const source = props.source || "Healthsites.io";

        layer.bindPopup(`
          <div style="font-size:12px">
            <b>${name}</b><br/>
            Type: ${type}<br/>
            Operator: ${operator}<br/>
            Source: ${source}
          </div>
        `);
      }}
    />
  );
}
