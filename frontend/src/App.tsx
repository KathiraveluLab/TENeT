import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { fetchRegions, CATRegion, Season } from './api/catApi';
import RegionMarker from './components/RegionMarker';
import Legend from './components/Legend';
import SeasonSelector from './components/SeasonSelector';

// Fix for default marker icons in React-Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Alaska-specific coordinates - Geographic center of Alaska
const ALASKA_CENTER: [number, number] = [64.2008, -149.4937];
const ALASKA_ZOOM = 5;

// Alaska boundary coordinates to restrict map view
const ALASKA_BOUNDS: [[number, number], [number, number]] = [
  [51.0, -180.0], // Southwest (includes Aleutian Islands)
  [71.5, -129.0]  // Northeast
];

function App() {
  const [regions, setRegions] = useState<CATRegion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [season, setSeason] = useState<Season>('year_round');

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const data = await fetchRegions(season);  // Pass season to get adjusted tiers
        setRegions(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
        console.error('Error loading regions:', err);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [season]);  // Re-fetch when season changes

  // Get season display info
  const getSeasonInfo = () => {
    switch (season) {
      case 'summer': return { icon: '☀️', label: 'Summer', note: 'All transport modes available' };
      case 'winter': return { icon: '❄️', label: 'Winter', note: 'Seasonal roads/water routes restricted' };
      case 'year_round': return { icon: '📅', label: 'Year-Round Average', note: 'Conservative average assumptions' };
    }
  };

  const seasonInfo = getSeasonInfo();

  return (
    <div style={{ height: '100vh', width: '100%', margin: 0, padding: 0, display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        backgroundColor: '#1e40af',
        color: 'white',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 'bold' }}>
              TENeT - Telehealth Effectiveness and Necessity Tracker
            </h1>
            <p style={{ margin: '5px 0 0 0', fontSize: '14px', opacity: 0.9 }}>
              Identifying healthcare deserts and assessing network feasibility for telehealth in Alaska
            </p>
          </div>
          <SeasonSelector season={season} onChange={setSeason} />
        </div>
      </div>

      {/* Season Indicator Banner */}
      <div style={{
        padding: '8px 20px',
        backgroundColor: '#dbeafe',
        borderBottom: '1px solid #bfdbfe',
        fontSize: '13px',
        color: '#1e40af',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
      }}>
        <span style={{ fontSize: '16px' }}>{seasonInfo.icon}</span>
        <span>
          <strong>Active Scenario:</strong> {seasonInfo.label} — {seasonInfo.note}
        </span>
        <span style={{
          marginLeft: 'auto',
          fontSize: '11px',
          color: '#6b7280',
          fontStyle: 'italic'
        }}>
          Click a community marker for season-adjusted telehealth priority
        </span>
      </div>

      {/* Map Container */}
      <div style={{ flex: 1, position: 'relative' }}>
        {/* Loading/Error overlay */}
        {loading && (
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            zIndex: 1000,
            backgroundColor: 'white',
            padding: '20px 40px',
            borderRadius: '8px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            fontSize: '16px',
            fontWeight: '500'
          }}>
            Loading community data...
          </div>
        )}

        {error && (
          <div style={{
            position: 'absolute',
            top: '10px',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 1000,
            backgroundColor: '#fee2e2',
            color: '#dc2626',
            padding: '12px 24px',
            borderRadius: '6px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            fontSize: '14px'
          }}>
            ⚠️ {error}
          </div>
        )}

        <MapContainer
          center={ALASKA_CENTER}
          zoom={ALASKA_ZOOM}
          maxBounds={ALASKA_BOUNDS}
          maxBoundsViscosity={1.0}
          minZoom={4}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* Render markers for all regions with season prop */}
          {regions.map(region => (
            <RegionMarker key={region.region_code} region={region} season={season} />
          ))}
        </MapContainer>

        {/* Legend */}
        {!loading && <Legend totalRegions={regions.length} />}
      </div>

      {/* Footer */}
      <div style={{
        padding: '12px 20px',
        backgroundColor: '#1f2937',
        color: '#9ca3af',
        fontSize: '12px',
        borderTop: '1px solid #374151'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <strong style={{ color: '#e5e7eb' }}>Mentors:</strong> Pradeeban Kathiravelu & David Moxley |
            <span style={{ marginLeft: '10px' }}>University of Alaska</span>
          </div>
          <div>
            <a
              href="https://github.com/KathiraveluLab/TENeT"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#60a5fa', textDecoration: 'none' }}
            >
              GitHub
            </a>
            {' | '}
            <a
              href="https://github.com/KathiraveluLab/TENeT/discussions"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#60a5fa', textDecoration: 'none' }}
            >
              Discussions
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;

