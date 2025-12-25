import React from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { CATRegion, getTierColor, getTierLabel } from '../api/catApi';

interface RegionMarkerProps {
    region: CATRegion;
}

/**
 * Create a custom circle marker icon with tier-based color
 */
function createTierIcon(tier: number): L.DivIcon {
    const color = getTierColor(tier);

    return L.divIcon({
        className: 'custom-marker',
        html: `
            <div style="
                width: 12px;
                height: 12px;
                background-color: ${color};
                border: 2px solid white;
                border-radius: 50%;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            "></div>
        `,
        iconSize: [12, 12],
        iconAnchor: [6, 6],
        popupAnchor: [0, -6],
    });
}

/**
 * Marker component for a CAT region with color-coded tier display
 */
export default function RegionMarker({ region }: RegionMarkerProps) {
    // Skip regions without coordinates
    if (region.centroid_lat === null || region.centroid_lon === null) {
        return null;
    }

    const icon = createTierIcon(region.tier_level);
    const tierColor = getTierColor(region.tier_level);
    const tierLabel = getTierLabel(region.tier_level);

    return (
        <Marker
            position={[region.centroid_lat, region.centroid_lon]}
            icon={icon}
        >
            <Popup>
                <div style={{ minWidth: '200px' }}>
                    <h3 style={{
                        margin: '0 0 8px 0',
                        color: '#1e40af',
                        fontSize: '16px',
                        fontWeight: 'bold'
                    }}>
                        {region.region_name}
                    </h3>

                    <div style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: '12px',
                        backgroundColor: tierColor,
                        color: 'white',
                        fontSize: '12px',
                        fontWeight: '600',
                        marginBottom: '8px'
                    }}>
                        Tier {region.tier_level}
                    </div>

                    <div style={{ fontSize: '13px', color: '#374151' }}>
                        <strong>Access Level:</strong> {tierLabel}
                    </div>

                    {region.access_score !== null && (
                        <div style={{ fontSize: '13px', color: '#374151', marginTop: '4px' }}>
                            <strong>Access Score:</strong> {region.access_score}
                        </div>
                    )}

                    {region.description && (
                        <div style={{
                            fontSize: '12px',
                            color: '#6b7280',
                            marginTop: '6px',
                            fontStyle: 'italic'
                        }}>
                            {region.description}
                        </div>
                    )}

                    <div style={{
                        fontSize: '11px',
                        color: '#9ca3af',
                        marginTop: '8px',
                        borderTop: '1px solid #e5e7eb',
                        paddingTop: '6px'
                    }}>
                        Code: {region.region_code}
                    </div>
                </div>
            </Popup>
        </Marker>
    );
}
