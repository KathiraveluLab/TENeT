import React, { useState, useCallback } from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import {
    CATRegion,
    getTierColor,
    getTierLabel,
    Season,
    TelehealthPriorityResponse,
    fetchTelehealthPriority,
    getPriorityColor
} from '../api/catApi';

interface RegionMarkerProps {
    region: CATRegion;
    season: Season;
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
 * and season-adjusted telehealth priority on popup open
 */
export default function RegionMarker({ region, season }: RegionMarkerProps) {
    const [priority, setPriority] = useState<TelehealthPriorityResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Fetch priority data when popup opens
    const handlePopupOpen = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await fetchTelehealthPriority(region.region_code, season);
            setPriority(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch priority');
            console.error('Error fetching priority:', err);
        } finally {
            setLoading(false);
        }
    }, [region.region_code, season]);

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
            eventHandlers={{
                popupopen: handlePopupOpen,
            }}
        >
            <Popup>
                <div style={{ minWidth: '260px' }}>
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

                    {/* Season-Adjusted Priority Section */}
                    <div style={{
                        marginTop: '12px',
                        paddingTop: '10px',
                        borderTop: '1px solid #e5e7eb'
                    }}>
                        <div style={{
                            fontSize: '12px',
                            fontWeight: '600',
                            color: '#6b7280',
                            marginBottom: '6px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px'
                        }}>
                            📊 Telehealth Priority
                            {priority?.season_scenario && (
                                <span style={{
                                    fontSize: '10px',
                                    fontWeight: 'normal',
                                    color: '#9ca3af'
                                }}>
                                    ({priority.season_scenario.season_display})
                                </span>
                            )}
                        </div>

                        {loading && (
                            <div style={{
                                fontSize: '12px',
                                color: '#6b7280',
                                fontStyle: 'italic'
                            }}>
                                Loading...
                            </div>
                        )}

                        {error && (
                            <div style={{
                                fontSize: '12px',
                                color: '#dc2626'
                            }}>
                                {error}
                            </div>
                        )}

                        {priority && !loading && (
                            <>
                                {/* Priority Badge */}
                                <div style={{
                                    display: 'inline-block',
                                    padding: '4px 10px',
                                    borderRadius: '4px',
                                    backgroundColor: getPriorityColor(priority.priority),
                                    color: 'white',
                                    fontSize: '12px',
                                    fontWeight: '600',
                                    marginBottom: '8px'
                                }}>
                                    {priority.label}
                                </div>

                                {/* Scores */}
                                <div style={{
                                    fontSize: '12px',
                                    color: '#374151',
                                    display: 'grid',
                                    gridTemplateColumns: '1fr 1fr',
                                    gap: '4px 12px',
                                    marginBottom: '8px'
                                }}>
                                    <div>
                                        <strong>Need Score:</strong> {priority.necessity_score}
                                    </div>
                                    <div>
                                        <strong>Connectivity:</strong> {priority.connectivity_score}%
                                    </div>
                                </div>

                                {/* Recommendation */}
                                <div style={{
                                    fontSize: '11px',
                                    color: '#6b7280',
                                    backgroundColor: '#f3f4f6',
                                    padding: '6px 8px',
                                    borderRadius: '4px',
                                    lineHeight: '1.4'
                                }}>
                                    {priority.recommendation}
                                </div>

                                {/* Season Note */}
                                <div style={{
                                    fontSize: '10px',
                                    color: '#9ca3af',
                                    marginTop: '6px',
                                    fontStyle: 'italic'
                                }}>
                                    {priority.season_scenario?.season_display} scenario applied
                                </div>
                            </>
                        )}
                    </div>

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

