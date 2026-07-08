import React, { useEffect, useState } from 'react';
import {
    DataGapsSummary,
    fetchDataGapsSummary,
    getConfidenceColor,
    getDataGapInfo
} from '../api/catApi';
import './DataCoveragePanel.css';

interface DataCoveragePanelProps {
    isExpanded?: boolean;
    onToggle?: () => void;
    totalRegions?: number;
}

/**
 * Panel showing data coverage and data gaps summary
 * Supports the 'data coverage/confidence' layer visualization
 */
export default function DataCoveragePanel({ isExpanded = false, onToggle, totalRegions }: DataCoveragePanelProps) {
    const [summary, setSummary] = useState<DataGapsSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadData() {
            try {
                setLoading(true);
                const data = await fetchDataGapsSummary();
                setSummary(data);
                setError(null);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load data gaps');
                console.error('Error loading data gaps:', err);
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, []);

    const renderShell = (content: React.ReactNode) => (
        <div className="data-coverage-hover">
            <button type="button" className="data-coverage-trigger" aria-label="Show data coverage layer legend">
                Data
            </button>
            <div className="data-coverage-panel" style={panelStyle}>
                {content}
            </div>
        </div>
    );

    if (loading) {
        return renderShell(
            <>
                <div style={{ padding: '24px 24px 8px 24px', fontSize: '16px', fontWeight: '500', color: '#181d26' }}>
                    <span>Data Coverage Layer</span>
                </div>
                <div style={{ padding: '8px 24px 24px 24px', fontSize: '12px', color: '#41454d' }}>
                    Loading...
                </div>
            </>
        );
    }

    if (error || !summary) {
        return renderShell(
            <>
                <div style={{ padding: '24px 24px 8px 24px', fontSize: '16px', fontWeight: '500', color: '#181d26' }}>
                    <span>Data Coverage Layer</span>
                </div>
                <div style={{ padding: '8px 24px 24px 24px', fontSize: '12px', color: '#dc2626' }}>
                    {error || 'No data available'}
                </div>
            </>
        );
    }

    const gapsPercentage = Math.round((summary.places_with_gaps / summary.total_places) * 100);
    const satellitePercent = Math.round((summary.primary_access.SATELLITE / summary.total_places) * 100);

    return renderShell(
        <>
            {/* Header */}
            <div
                style={{ 
                    padding: '24px 24px 8px 24px', 
                    fontSize: '16px', 
                    fontWeight: '500', 
                    color: '#181d26', 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'space-between',
                    cursor: onToggle ? 'pointer' : 'default' 
                }}
                onClick={onToggle}
            >
                <span>Data Coverage Layer</span>
                {onToggle && (
                    <span style={{ fontSize: '10px', marginLeft: '8px', color: '#9297a0' }}>
                        {isExpanded ? '▼' : '▶'}
                    </span>
                )}
            </div>

            {/* Quick Stats */}
            <div style={{ padding: '8px 24px 16px 24px' }}>
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '16px'
                }}>
                    <div>
                        <div style={{ color: '#41454d', fontSize: '12px', marginBottom: '4px' }}>Total Places</div>
                        <div style={{ fontWeight: '400', fontSize: '24px', color: '#181d26', letterSpacing: '-0.02em' }}>
                            {summary.total_places}
                        </div>
                    </div>
                    <div>
                        <div style={{ color: '#41454d', fontSize: '12px', marginBottom: '4px' }}>With Data Gaps</div>
                        <div style={{ fontWeight: '400', fontSize: '24px', color: '#aa2d00', letterSpacing: '-0.02em' }}>
                            {summary.places_with_gaps} <span style={{ fontSize: '13px', fontWeight: '400', color: '#aa2d00' }}>({gapsPercentage}%)</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Confidence Distribution */}
            <div style={{ padding: '16px 24px' }}>
                <div style={{ fontSize: '12px', color: '#181d26', marginBottom: '12px', fontWeight: '500' }}>
                    Data Confidence
                </div>
                <div style={{ display: 'flex', gap: '2px', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                    <div
                        style={{
                            flex: summary.confidence_distribution.HIGH,
                            backgroundColor: '#006400',
                            minWidth: summary.confidence_distribution.HIGH > 0 ? '4px' : '0'
                        }}
                    />
                    <div
                        style={{
                            flex: summary.confidence_distribution.MEDIUM,
                            backgroundColor: '#f4d35e',
                            minWidth: summary.confidence_distribution.MEDIUM > 0 ? '4px' : '0'
                        }}
                    />
                    <div
                        style={{
                            flex: summary.confidence_distribution.LOW,
                            backgroundColor: '#aa2d00',
                            minWidth: summary.confidence_distribution.LOW > 0 ? '4px' : '0'
                        }}
                    />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px', fontSize: '11px', color: '#41454d' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: '#006400' }} />
                        High
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: '#f4d35e' }} />
                        Med
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: '#aa2d00' }} />
                        Low
                    </span>
                </div>
            </div>

            {/* Primary Access Type */}
            <div style={{ padding: '16px 24px' }}>
                <div style={{ fontSize: '12px', color: '#181d26', marginBottom: '12px', fontWeight: '500' }}>
                    Primary Internet Access
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                    <div style={{
                        flex: 1,
                        padding: '12px',
                        borderRadius: '6px',
                        backgroundColor: '#f8fafc',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center'
                    }}>
                        <div style={{ fontWeight: '400', color: '#181d26', fontSize: '18px' }}>{satellitePercent}%</div>
                        <div style={{ color: '#41454d', fontSize: '12px', marginTop: '4px' }}>Satellite</div>
                    </div>
                    <div style={{
                        flex: 1,
                        padding: '12px',
                        borderRadius: '6px',
                        backgroundColor: '#f8fafc',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center'
                    }}>
                        <div style={{ fontWeight: '400', color: '#181d26', fontSize: '18px' }}>{100 - satellitePercent}%</div>
                        <div style={{ color: '#41454d', fontSize: '12px', marginTop: '4px' }}>Wired</div>
                    </div>
                </div>
            </div>

            {/* Expanded: Gap Breakdown */}
            {(isExpanded || !onToggle) && (
                <div style={{ padding: '10px 12px' }}>
                    <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '6px', fontWeight: '600' }}>
                        Data Gap Types
                    </div>
                    {Object.entries(summary.gap_breakdown)
                        .filter(([_, data]) => data.count > 0)
                        .sort(([_, a], [__, b]) => b.count - a.count)
                        .slice(0, 5)
                        .map(([gapType, data]) => {
                            const info = getDataGapInfo(gapType);
                            return (
                                <div key={gapType} style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    padding: '4px 0',
                                    fontSize: '11px',
                                    borderBottom: '1px solid #f3f4f6'
                                }}>
                                    <span>{info.label}</span>
                                    <span style={{
                                        color: info.severity === 'error' ? '#dc2626' :
                                            info.severity === 'warning' ? '#f97316' : '#6b7280',
                                        fontWeight: '500'
                                    }}>
                                        {data.count} ({data.percentage}%)
                                    </span>
                                </div>
                            );
                        })}
                </div>
            )}

            {/* Footer Note */}
            <div style={{
                padding: '16px 24px 24px 24px',
                fontSize: '11px',
                color: '#9297a0'
            }}>
                Data source: FCC Broadband Availability
            </div>
        </>
    );
}

// Airtable Styles (Flat Canvas, Hairline Border)
const panelStyle: React.CSSProperties = {
    minWidth: '240px',
    maxWidth: '280px',
    background: '#ffffff',
    borderRadius: '10px',
    border: '1px solid #dddddd',
    fontSize: '13px',
    overflow: 'hidden',
    fontFamily: 'inherit'
};
