const map = L.map("map");

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "© OpenStreetMap contributors"
}).addTo(map);


const zoneLayer = L.layerGroup();

fetch("alaska_telehealth.geojson")
  .then(res => res.json())
  .then(data => {
    const geoLayer = L.geoJSON(data, {
      style: feature => {
        let color;
        if (feature.properties.clinic_count < 3) {
          color = "#d7191c"; 
        } else {
          color = "#1a9641"; 
        }

        return {
          fillColor: color,
          weight: 1,
          color: "#333",
          fillOpacity: 0.65
        };
      },
      onEachFeature: (feature, layer) => {
        layer.bindPopup(`
          <b>Clinics:</b> ${feature.properties.clinic_count}<br>
          <b>Status:</b> ${
            feature.properties.clinic_count < 3
              ? "Healthcare Desert"
              : "Adequate Healthcare"
          }<br>
          <b>Avg Download:</b> ${
            feature.properties.avg_download
              ? feature.properties.avg_download.toFixed(1)
              : "N/A"
          } Mbps
        `);
      }
    });

    geoLayer.addTo(zoneLayer);
    zoneLayer.addTo(map);

   
    map.fitBounds(geoLayer.getBounds());
  });

const clinicLayer = L.layerGroup();

fetch("clinics.geojson")
  .then(res => res.json())
  .then(data => {
    L.geoJSON(data, {
      pointToLayer: (feature, latlng) =>
        L.circleMarker(latlng, {
          radius: 5,
          color: "#005eff",
          fillColor: "#005eff",
          fillOpacity: 0.9
        }),
      onEachFeature: (feature, layer) => {
        layer.bindPopup(
          feature.properties.name
            ? `<b>${feature.properties.name}</b>`
            : "<b>Healthcare Facility</b>"
        );
      }
    }).addTo(clinicLayer);
  });

clinicLayer.addTo(map);

L.control.layers(
  {
    "Telehealth Zones (Polygons)": zoneLayer,
    "Clinic Locations (Points)": clinicLayer
  },
  null,
  { collapsed: false }
).addTo(map);
