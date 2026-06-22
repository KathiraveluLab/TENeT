/**
 * ScenarioLayer – renders scenario-colored markers on the map.
 *
 * When scenario mode is active, this layer replaces the baseline CAT markers
 * with scenario-colored markers that match the CAT layer marker styling.
 * Clicking updates selectedRegionCode.
 */
import React, { memo } from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import type { ScenarioPreviewResponse, ScenarioRegion } from '../../types/scenario';
import { getScenarioStatusColor, getScenarioDeltaColor } from '../../types/scenario';

interface ScenarioLayerProps {
    data: ScenarioPreviewResponse | null;
    active: boolean;
    selectedRegionCode: string | null;
    onSelect: (regionCode: string) => void;
    onViewDetails: (regionCode: string) => void;
    onMarkerReady?: (regionCode: string, marker: L.Marker | null) => void;
}

const markerIconCache = new Map<string, L.DivIcon>();

function createMarkerIcon(color: string, selected = false): L.DivIcon {
    const cacheKey = `${color}:${selected ? 'selected' : 'default'}`;
    const cached = markerIconCache.get(cacheKey);
    if (cached) return cached;

    const size = selected ? 16 : 10;
    const anchor = size / 2;
    const icon = L.divIcon({
        className: 'custom-marker scenario-marker',
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
    markerIconCache.set(cacheKey, icon);
    return icon;
}

function statusLabel(status: string): string {
    return status
        .toLowerCase()
        .split('_')
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');
}

function deltaSymbol(delta: string): string {
    switch (delta) {
        case 'improved': return '▲';
        case 'worsened': return '▼';
        default: return '—';
    }
}

interface ScenarioMarkerProps {
    region: ScenarioRegion;
    selected: boolean;
    onSelect: (regionCode: string) => void;
    onViewDetails: (regionCode: string) => void;
    onMarkerReady?: (regionCode: string, marker: L.Marker | null) => void;
}

const ScenarioMarker = memo(function ScenarioMarker({
    region,
    selected,
    onSelect,
    onViewDetails,
    onMarkerReady,
}: ScenarioMarkerProps) {
    if (region.lat === null || region.lon === null) return null;

    const color = getScenarioStatusColor(region.scenario_status);
    return (
        <Marker
            position={[region.lat, region.lon]}
            icon={createMarkerIcon(color, selected)}
            eventHandlers={{
                click: () => onSelect(region.region_code),
            }}
            ref={(marker) => {
                onMarkerReady?.(region.region_code, marker);
            }}
        >
            <Popup maxWidth={280}>
                <div style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: '13px',
                    lineHeight: 1.5,
                }}>
                    <div style={{
                        fontWeight: 700,
                        fontSize: '14px',
                        marginBottom: '8px',
                        color: '#0f172a',
                    }}>
                        {region.name}
                    </div>

                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'auto 1fr',
                        gap: '4px 12px',
                        marginBottom: '10px',
                    }}>
                        <span style={{ color: '#64748b' }}>Baseline Status</span>
                        <strong style={{ color: getScenarioStatusColor(region.baseline_status) }}>
                            {statusLabel(region.baseline_status)}
                        </strong>

                        <span style={{ color: '#64748b' }}>Scenario Status</span>
                        <strong style={{ color: getScenarioStatusColor(region.scenario_status) }}>
                            {statusLabel(region.scenario_status)}
                        </strong>

                        {region.changed && (
                            <>
                                <span style={{ color: '#64748b' }}>Change</span>
                                <strong style={{ color: getScenarioDeltaColor(region.status_delta) }}>
                                    {deltaSymbol(region.status_delta)} {region.status_delta}
                                </strong>
                            </>
                        )}

                        <span style={{ color: '#64748b' }}>Need Score</span>
                        <strong>{region.scenario_need_score}</strong>
                    </div>

                    <div style={{
                        fontSize: '11px',
                        color: '#64748b',
                        fontStyle: 'italic',
                        borderTop: '1px solid #e2e8f0',
                        paddingTop: '8px',
                        lineHeight: 1.4,
                    }}>
                        This scenario result is modeled from selected thresholds
                        and should not be interpreted as observed field data.
                    </div>

                    <button
                        type="button"
                        onClick={() => onViewDetails(region.region_code)}
                        style={{
                            marginTop: '8px',
                            padding: '5px 12px',
                            border: '1px solid #e2e8f0',
                            borderRadius: '6px',
                            background: 'white',
                            color: '#475569',
                            fontSize: '12px',
                            fontWeight: 600,
                            cursor: 'pointer',
                            width: '100%',
                        }}
                    >
                        View Details →
                    </button>
                </div>
            </Popup>
        </Marker>
    );
});

export default function ScenarioLayer({
    data,
    active,
    selectedRegionCode,
    onSelect,
    onViewDetails,
    onMarkerReady,
}: ScenarioLayerProps) {
    if (!active || !data) return null;

    return (
        <>
            {data.regions.map(region => (
                <ScenarioMarker
                    key={region.region_code}
                    region={region}
                    selected={region.region_code === selectedRegionCode}
                    onSelect={onSelect}
                    onViewDetails={onViewDetails}
                    onMarkerReady={onMarkerReady}
                />
            ))}
        </>
    );
}

/* ─── Scenario Sidebar Card ────────────────────────────────────────────── */

interface ScenarioSidebarCardProps {
    region: ScenarioRegion | undefined;
}

export function ScenarioSidebarCard({ region }: ScenarioSidebarCardProps) {
    if (!region) return null;

    return (
        <section style={{
            margin: '12px 0',
            padding: '14px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, rgba(124,58,237,0.06) 0%, rgba(124,58,237,0.02) 100%)',
            border: '1px solid rgba(124,58,237,0.15)',
        }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '10px',
            }}>
                <span style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    color: '#7c3aed',
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                }}>
                    Scenario Estimate
                </span>
                <span style={{
                    display: 'inline-block',
                    background: 'linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)',
                    color: 'white',
                    fontSize: '9px',
                    fontWeight: 700,
                    padding: '1px 6px',
                    borderRadius: '3px',
                    letterSpacing: '0.04em',
                }}>
                    MODELED
                </span>
            </div>

            <div style={{
                display: 'grid',
                gridTemplateColumns: 'auto 1fr',
                gap: '4px 12px',
                fontSize: '12px',
            }}>
                <span style={{ color: '#64748b' }}>Baseline Status</span>
                <strong style={{ color: getScenarioStatusColor(region.baseline_status) }}>
                    {statusLabel(region.baseline_status)}
                </strong>

                <span style={{ color: '#64748b' }}>Scenario Status</span>
                <strong style={{ color: getScenarioStatusColor(region.scenario_status) }}>
                    {statusLabel(region.scenario_status)}
                </strong>

                <span style={{ color: '#64748b' }}>Need Score Delta</span>
                <strong style={{
                    color: region.need_score_delta < 0
                        ? '#22c55e'
                        : region.need_score_delta > 0
                            ? '#ef4444'
                            : '#94a3b8',
                }}>
                    {region.need_score_delta > 0 ? '+' : ''}{region.need_score_delta}
                </strong>
            </div>

            {/* Reason codes */}
            {region.reason_codes.length > 0 && (
                <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '4px',
                    marginTop: '8px',
                }}>
                    {region.reason_codes.map(code => (
                        <span
                            key={code}
                            style={{
                                fontSize: '10px',
                                fontWeight: 600,
                                color: '#64748b',
                                background: 'rgba(0,0,0,0.04)',
                                padding: '2px 6px',
                                borderRadius: '3px',
                                fontFamily: 'monospace',
                            }}
                        >
                            {code}
                        </span>
                    ))}
                </div>
            )}

            {region.explanation && (
                <div style={{
                    fontSize: '11px',
                    color: '#64748b',
                    marginTop: '8px',
                    lineHeight: 1.4,
                }}>
                    {region.explanation}
                </div>
            )}
        </section>
    );
}

/* ─── Scenario Legend ──────────────────────────────────────────────────── */

export function ScenarioLegend() {
    const STATUS_ITEMS = [
        { status: 'TELEHEALTH_READY', label: 'Telehealth Ready' },
        { status: 'COMMUNITY_ANCHOR', label: 'Community Anchor' },
        { status: 'LIMITED_TELEHEALTH', label: 'Limited Telehealth' },
        { status: 'CRITICAL_GAP', label: 'Critical Gap' },
        { status: 'DATA_UNAVAILABLE', label: 'Data Unavailable' },
    ];

    return (
        <div style={{
            position: 'absolute',
            bottom: '30px',
            left: '20px',
            zIndex: 1000,
            background: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            padding: '14px 16px',
            borderRadius: '10px',
            boxShadow: '0 4px 16px rgba(31, 38, 135, 0.1)',
            border: '1px solid rgba(255, 255, 255, 0.3)',
            fontSize: '12px',
            fontFamily: "'Inter', sans-serif",
            maxWidth: '200px',
        }}>
            <div style={{
                fontWeight: 700,
                fontSize: '12px',
                color: '#0f172a',
                marginBottom: '4px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
            }}>
                What-If Scenario
                <span style={{
                    fontSize: '9px',
                    fontWeight: 700,
                    color: '#334155',
                    background: '#e2e8f0',
                    padding: '1px 5px',
                    borderRadius: '3px',
                }}>
                    MODELED
                </span>
            </div>

            <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
                marginTop: '8px',
            }}>
                {STATUS_ITEMS.map(item => (
                    <div
                        key={item.status}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                        }}
                    >
                        <span style={{
                            width: '10px',
                            height: '10px',
                            borderRadius: '50%',
                            background: getScenarioStatusColor(item.status),
                            flexShrink: 0,
                        }} />
                        <span style={{ color: '#475569', fontSize: '11px' }}>
                            {item.label}
                        </span>
                    </div>
                ))}
            </div>

            <div style={{
                fontSize: '10px',
                color: '#94a3b8',
                marginTop: '8px',
                lineHeight: 1.4,
                fontStyle: 'italic',
            }}>
                Scenario colors represent modeled telehealth readiness under the selected thresholds.
                Baseline data remains unchanged.
            </div>
        </div>
    );
}
