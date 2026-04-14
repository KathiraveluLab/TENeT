import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icons in React Leaflet
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});

L.Marker.prototype.options.icon = DefaultIcon;

interface FacilityProperties {
    name: string;
    type: string;
    source: string;
}

interface FacilityFeature {
    type: string;
    geometry: {
        type: string;
        coordinates: [number, number];
    };
    properties: FacilityProperties;
}

interface FeatureCollection {
    type: string;
    features: FacilityFeature[];
}

const MapComponent: React.FC = () => {
    const [geojsonData, setGeojsonData] = useState<FeatureCollection | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Fetch the Alaska healthsites GeoJSON from the backend
        fetch('http://localhost:8000/data/raw/alaska_healthsites.geojson')
            .then(res => {
                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                return res.json();
            })
            .then(data => {
                setGeojsonData(data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error loading geojson:", err);
                setLoading(false);
            });
    }, []);

    const position: [number, number] = [64.0, -153.0]; // Center of Alaska

    if (loading) return <div>Loading Map...</div>;

    return (
        <MapContainer 
            center={position} 
            zoom={5} 
            style={{ height: '100vh', width: '100%' }}
        >
            <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {geojsonData?.features.map((feature, idx) => (
                <Marker 
                    key={idx} 
                    position={[feature.geometry.coordinates[1], feature.geometry.coordinates[0]]}
                >
                    <Popup>
                        <strong>{feature.properties.name}</strong><br />
                        Type: {feature.properties.type}<br />
                        Source: {feature.properties.source}
                    </Popup>
                </Marker>
            ))}
        </MapContainer>
    );
};

export default MapComponent;
