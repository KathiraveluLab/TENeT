import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import {
    CATRegion,
    getTierColor,
    getTierLabel,
    getNeedColor,
    getNeedLabel,
    Season,
    TelehealthPriorityResponse,
    fetchTelehealthPriority,
    getPriorityColor,
    BroadbandCoverage,
    getConfidenceColor,
    getDataGapInfo,
    HealthcareByRegion,
    fetchHealthcareByRegion,
    getFacilityTypeInfo,
    RegionAffordability,
    SafetyNetClassification,
    fetchRegionAffordability,
    fetchRegionSafetyNet,
    TelehealthStatus,
    fetchTelehealthStatus,
    getTelehealthStatusColor
} from '../api/catApi';

interface RegionMarkerProps {
    region: CATRegion;
    season: Season;
    selected?: boolean;
    onSelect?: (regionCode: string) => void;
    onMarkerReady?: (regionCode: string, marker: L.Marker | null) => void;
}

// API base for fetching broadband data
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/cat';

/**
 * Create a custom circle marker icon with dynamic color - "Gemstone" style
 */
function createMarkerIcon(color: string, selected = false): L.DivIcon {
    const size = selected ? 16 : 10;
    const anchor = size / 2;
    return L.divIcon({
        className: 'custom-marker',
        html: `
            <div style="
                width: ${size}px;
                height: ${size}px;
                background-color: ${color};
                opacity: ${selected ? 1 : 0.8};
                border: ${selected ? 3 : 1.5}px solid rgba(255, 255, 255, 0.95);
                border-radius: 50%;
                box-shadow: 0 ${selected ? 2 : 1}px ${selected ? 8 : 3}px rgba(0,0,0,0.25);
            "></div>
        `,
        iconSize: [size, size],
        iconAnchor: [anchor, anchor],
        popupAnchor: [0, -anchor],
    });
}

/**
 * Marker component for a CAT region with color-coded tier display
 * and season-adjusted telehealth priority on popup open
 */
export default function RegionMarker({
    region,
    season,
    selected = false,
    onSelect,
    onMarkerReady,
}: RegionMarkerProps) {
    const markerRef = useRef<L.Marker | null>(null);
    const [priority, setPriority] = useState<TelehealthPriorityResponse | null>(null);
    const [broadband, setBroadband] = useState<BroadbandCoverage | null>(null);
    const [healthcare, setHealthcare] = useState<HealthcareByRegion | null>(null);
    const [affordability, setAffordability] = useState<RegionAffordability | null>(null);
    const [safetyNet, setSafetyNet] = useState<SafetyNetClassification | null>(null);
    const [telehealthStatus, setTelehealthStatus] = useState<TelehealthStatus | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Fetch priority, broadband, and healthcare data when popup opens
    const handlePopupOpen = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            // Fetch telehealth priority
            const priorityData = await fetchTelehealthPriority(region.region_code, season);
            setPriority(priorityData);

            // Try to fetch broadband data by matching region name
            try {
                const response = await fetch(`${API_BASE}/broadband`);
                if (response.ok) {
                    const data = await response.json();
                    // Find matching place by name (case-insensitive partial match)
                    const regionName = region.region_name.toLowerCase();
                    const match = data.broadband?.find((b: BroadbandCoverage) =>
                        b.place_name.toLowerCase().includes(regionName) ||
                        regionName.includes(b.place_name.toLowerCase()) ||
                        b.region_code === region.region_code
                    );
                    if (match) {
                        setBroadband(match);
                    }
                }
            } catch (bbErr) {
                console.warn('Could not fetch broadband data:', bbErr);
            }

            // Fetch healthcare facilities near this region
            try {
                const healthcareData = await fetchHealthcareByRegion(region.region_code, 5);
                setHealthcare(healthcareData);
            } catch (hcErr) {
                console.warn('Could not fetch healthcare data:', hcErr);
            }

            // Fetch affordability analysis
            try {
                const affordData = await fetchRegionAffordability(region.region_code);
                setAffordability(affordData);
            } catch (affErr) {
                console.warn('Could not fetch affordability data:', affErr);
            }

            // Fetch safety net classification
            try {
                const safetyData = await fetchRegionSafetyNet(region.region_code);
                setSafetyNet(safetyData);
            } catch (snErr) {
                console.warn('Could not fetch safety net data:', snErr);
            }

            // Fetch composite telehealth status (for marker color)
            try {
                const statusData = await fetchTelehealthStatus(region.region_code);
                setTelehealthStatus(statusData);
            } catch (tsErr) {
                console.warn('Could not fetch telehealth status:', tsErr);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch priority');
            console.error('Error fetching priority:', err);
        } finally {
            setLoading(false);
        }
    }, [region.region_code, region.region_name, season]);

    useEffect(() => {
        onMarkerReady?.(region.region_code, markerRef.current);
        return () => onMarkerReady?.(region.region_code, null);
    }, [onMarkerReady, region.region_code]);

    // Skip regions without coordinates
    if (region.centroid_lat === null || region.centroid_lon === null) {
        return null;
    }

    // Use need score to color marker
    const markerColor = getNeedColor(region.necessity_score);
    const icon = createMarkerIcon(markerColor, selected);
    const needColor = getNeedColor(region.necessity_score);
    const needLabel = getNeedLabel(region.necessity_score);

    return (
        <Marker
            ref={markerRef}
            position={[region.centroid_lat, region.centroid_lon]}
            icon={icon}
            eventHandlers={{
                click: () => onSelect?.(region.region_code),
                popupopen: handlePopupOpen,
            }}
        >
            <Popup
                autoPan
                keepInView
                maxWidth={420}
                minWidth={320}
                autoPanPaddingTopLeft={[64, 120]}
                autoPanPaddingBottomRight={[64, 80]}
            >
                <div style={{
                    minWidth: '300px',
                    maxWidth: '390px',
                    maxHeight: 'min(68vh, 620px)',
                    overflowY: 'auto',
                    paddingRight: '4px'
                }}>
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
                        backgroundColor: needColor,
                        color: 'white',
                        fontSize: '12px',
                        fontWeight: '600',
                        marginBottom: '8px'
                    }}>
                        Telehealth Need Score: {region.necessity_score}
                    </div>

                    <div style={{ fontSize: '13px', color: '#374151' }}>
                        <strong>Telehealth Priority:</strong> {needLabel}
                    </div>

                    {/* AFFORDABILITY & SAFETY NET BADGES */}
                    {!loading && (affordability || safetyNet) && (
                        <div style={{
                            display: 'flex',
                            gap: '6px',
                            flexWrap: 'wrap',
                            marginTop: '8px'
                        }}>
                            {/* Affordability Badge */}
                            {affordability && (
                                <div style={{
                                    display: 'inline-block',
                                    padding: '2px 8px',
                                    borderRadius: '12px',
                                    backgroundColor: affordability.has_income_data
                                        ? (affordability.is_affordable ? '#22c55e' : '#ef4444')
                                        : '#6b7280',
                                    color: 'white',
                                    fontSize: '10px',
                                    fontWeight: '600'
                                }}>
                                    {affordability.has_income_data
                                        ? (affordability.is_affordable
                                            ? `✓ Affordable (${affordability.burden_pct}%)`
                                            : `✗ Unaffordable (${affordability.burden_pct}%)`)
                                        : '? Income Data N/A'}
                                </div>
                            )}

                            {/* Safety Net Badge */}
                            {safetyNet && (
                                <div style={{
                                    display: 'inline-block',
                                    padding: '2px 8px',
                                    borderRadius: '12px',
                                    backgroundColor: safetyNet.classification_color,
                                    color: 'white',
                                    fontSize: '10px',
                                    fontWeight: '600'
                                }}>
                                    {safetyNet.classification === 'COMMUNITY_SUPPORTED'
                                        ? `Clinic ${safetyNet.nearest_clinic?.distance_km}km`
                                        : 'No Nearby Clinic'}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Affordability Details (when data available) */}
                    {!loading && affordability?.has_income_data && (
                        <div style={{
                            marginTop: '8px',
                            padding: '8px',
                            backgroundColor: affordability.is_affordable ? '#f0fdf4' : '#fef2f2',
                            border: `1px solid ${affordability.is_affordable ? '#86efac' : '#fecaca'}`,
                            borderRadius: '6px',
                            fontSize: '11px'
                        }}>
                            <div style={{ fontWeight: '600', color: '#374151', marginBottom: '4px' }}>
                                Affordability Gap Analysis
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px' }}>
                                <span>Median Income:</span>
                                <strong>${(affordability.median_income ?? 0).toLocaleString()}/yr</strong>
                                <span>Internet Cost:</span>
                                <strong>${affordability.internet_cost}/mo ({affordability.isp})</strong>
                                <span>Burden:</span>
                                <strong style={{ color: affordability.is_affordable ? '#166534' : '#dc2626' }}>
                                    {affordability.burden_pct}% of income
                                </strong>
                            </div>
                            <div style={{ marginTop: '4px', fontSize: '10px', color: '#6b7280' }}>
                                Source: ZCTA {affordability.zcta} ({affordability.distance_km}km away)
                            </div>
                        </div>
                    )}

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
                                    gridTemplateColumns: '1fr',
                                    gap: '4px',
                                    marginBottom: '8px'
                                }}>
                                    <div>
                                        <strong>Telehealth Need Score:</strong> {priority.necessity_score}
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

                    {/* Broadband Data Gaps Section */}
                    {broadband && (
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
                                Broadband Data
                                <span style={{
                                    fontSize: '10px',
                                    padding: '1px 6px',
                                    borderRadius: '4px',
                                    backgroundColor: getConfidenceColor(broadband.confidence),
                                    color: 'white',
                                    fontWeight: '500'
                                }}>
                                    {broadband.confidence}
                                </span>
                            </div>

                            {/* Coverage Stats */}
                            <div style={{
                                fontSize: '11px',
                                color: '#374151',
                                marginBottom: '6px'
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                                    <span>Primary Access:</span>
                                    <strong>{broadband.primary_access === 'SATELLITE' ? 'Satellite' : 'Wired'}</strong>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                                    <span>25 Mbps Coverage:</span>
                                    <strong>{broadband.coverage.any_tech_25mbps_pct !== null
                                        ? `${Math.round(broadband.coverage.any_tech_25mbps_pct * 100)}%`
                                        : 'N/A'}</strong>
                                </div>
                                {broadband.residential_units && (
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span>Residential Units:</span>
                                        <strong>{broadband.residential_units.toLocaleString()}</strong>
                                    </div>
                                )}
                            </div>

                            {/* Data Gaps */}
                            {broadband.data_gaps && broadband.data_gaps.length > 0 && (
                                <div style={{
                                    backgroundColor: '#fef3c7',
                                    border: '1px solid #f59e0b',
                                    borderRadius: '4px',
                                    padding: '6px 8px',
                                    fontSize: '10px'
                                }}>
                                    <div style={{ fontWeight: '600', color: '#92400e', marginBottom: '4px' }}>
                                        Data Quality Issues:
                                    </div>
                                    {broadband.data_gaps.map((gap, idx) => {
                                        const info = getDataGapInfo(gap);
                                        return (
                                            <div key={idx} style={{ color: '#78350f', marginLeft: '8px' }}>
                                                {info.icon} {info.label}
                                            </div>
                                        );
                                    })}
                                </div>
                            )}

                            {/* No Gaps */}
                            {(!broadband.data_gaps || broadband.data_gaps.length === 0) && (
                                <div style={{
                                    backgroundColor: '#dcfce7',
                                    border: '1px solid #22c55e',
                                    borderRadius: '4px',
                                    padding: '6px 8px',
                                    fontSize: '10px',
                                    color: '#166534'
                                }}>
                                    ✓ Broadband data complete
                                </div>
                            )}
                        </div>
                    )}

                    {/* DYNAMIC DATA AVAILABILITY SECTION */}
                    <div style={{
                        marginTop: '12px',
                        paddingTop: '10px',
                        borderTop: '1px solid #e5e7eb'
                    }}>
                        <div style={{
                            fontSize: '12px',
                            fontWeight: '600',
                            color: '#374151',
                            marginBottom: '6px'
                        }}>
                            Data Availability for {region.region_name}
                        </div>
                        <div style={{
                            backgroundColor: '#f9fafb',
                            border: '1px solid #e5e7eb',
                            borderRadius: '4px',
                            padding: '8px',
                            fontSize: '10px'
                        }}>
                            {/* Broadband Data */}
                            <div style={{ marginBottom: '6px' }}>
                                <strong style={{ color: '#374151' }}>Broadband Coverage:</strong>
                                {broadband ? (
                                    <div style={{ marginLeft: '8px', color: '#166534' }}>
                                        <div>✅ Speed coverage data (FCC)</div>
                                        <div>✅ Technology type ({broadband.primary_access})</div>
                                        <div>✅ Residential units ({broadband.residential_units?.toLocaleString() || 'N/A'})</div>
                                        {broadband.coverage.wired_25mbps_pct !== null && broadband.coverage.wired_25mbps_pct > 0 && (
                                            <div>✅ Wired coverage: {Math.round(broadband.coverage.wired_25mbps_pct * 100)}%</div>
                                        )}
                                        {(broadband.coverage.wired_25mbps_pct === null || broadband.coverage.wired_25mbps_pct === 0) && (
                                            <div style={{ color: '#dc2626' }}>❌ No wired infrastructure data</div>
                                        )}
                                    </div>
                                ) : (
                                    <div style={{ marginLeft: '8px', color: '#dc2626' }}>
                                        <div>❌ No FCC broadband data available</div>
                                    </div>
                                )}
                            </div>

                            {/* Network Quality */}
                            <div style={{ marginBottom: '6px' }}>
                                <strong style={{ color: '#374151' }}>Network Quality:</strong>
                                <div style={{ marginLeft: '8px' }}>
                                    {priority?.connectivity_details?.latency_ms ? (
                                        <div style={{ color: '#166534' }}>✅ Latency: {priority.connectivity_details.latency_ms}ms</div>
                                    ) : (
                                        <div style={{ color: '#dc2626' }}>❌ Latency data missing <em>(need RIPE Atlas)</em></div>
                                    )}
                                    {priority?.connectivity_details?.bandwidth_mbps ? (
                                        <div style={{ color: '#166534' }}>✅ Bandwidth: {priority.connectivity_details.bandwidth_mbps} Mbps</div>
                                    ) : (
                                        <div style={{ color: '#dc2626' }}>❌ Real bandwidth test missing <em>(need Ookla)</em></div>
                                    )}
                                    <div style={{ color: '#dc2626' }}>❌ Packet loss rate missing <em>(need monitoring)</em></div>
                                </div>
                            </div>

                            {/* Healthcare Access - Now using real OSM data */}
                            <div style={{ marginBottom: '6px' }}>
                                <strong style={{ color: '#374151' }}>Healthcare Access:</strong>
                                <div style={{ marginLeft: '8px' }}>
                                    {healthcare?.nearest_clinic ? (
                                        <div style={{ color: '#166534' }}>
                                            Nearest clinic: {healthcare.nearest_clinic.name.substring(0, 25)}{healthcare.nearest_clinic.name.length > 25 ? '...' : ''} ({healthcare.nearest_clinic.distance_km} km)
                                        </div>
                                    ) : (
                                        <div style={{ color: '#dc2626' }}>❌ No clinic data available</div>
                                    )}
                                    {healthcare?.nearest_hospital ? (
                                        <div style={{ color: '#166534' }}>
                                            ✅ Nearest hospital: {healthcare.nearest_hospital.name.substring(0, 25)}{healthcare.nearest_hospital.name.length > 25 ? '...' : ''} ({healthcare.nearest_hospital.distance_km} km)
                                        </div>
                                    ) : (
                                        <div style={{ color: '#dc2626' }}>❌ No hospital data available</div>
                                    )}
                                    {healthcare?.facilities && healthcare.facilities.some(f => f.has_emergency) ? (
                                        <div style={{ color: '#166534' }}>
                                            ✅ Emergency services: Yes ({healthcare.facilities.filter(f => f.has_emergency).length} facilities)
                                        </div>
                                    ) : (
                                        <div style={{ color: '#f97316' }}>⚠️ No emergency services found nearby</div>
                                    )}
                                </div>
                            </div>

                            {/* Demographics */}
                            <div>
                                <strong style={{ color: '#374151' }}>Demographics:</strong>
                                <div style={{ marginLeft: '8px' }}>
                                    {region.population ? (
                                        <div style={{ color: '#166534' }}>✅ Population: {region.population.toLocaleString()}</div>
                                    ) : (
                                        <div style={{ color: '#dc2626' }}>❌ Population data missing <em>(need Census)</em></div>
                                    )}
                                    <div style={{ color: '#dc2626' }}>❌ Age distribution missing <em>(need Census ACS)</em></div>
                                    <div style={{ color: '#dc2626' }}>❌ Health conditions missing <em>(need health records)</em></div>
                                </div>
                            </div>
                        </div>
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
