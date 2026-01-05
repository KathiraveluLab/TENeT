import React, { useEffect, useState } from 'react';
import {
    DataGapsSummary,
    fetchDataGapsSummary,
    getConfidenceColor,
    getDataGapInfo
} from '../api/catApi';

interface DataCoveragePanelProps {
    isExpanded?: boolean;
    onToggle?: () => void;
}

/**
 * Panel showing data coverage and data gaps summary
 * Supports the 'data coverage/confidence' layer visualization
 */
export default function DataCoveragePanel({ isExpanded = false, onToggle }: DataCoveragePanelProps) {
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

    if (loading) {
        return (
            <div style={panelStyle}>
                <div style={headerStyle}>
                    <span>📊 Data Coverage</span>
                </div>
                <div style={{ padding: '12px', fontSize: '12px', color: '#6b7280' }}>
                    Loading...
                </div>
            </div>
        );
    }

    if (error || !summary) {
        return (
            <div style={panelStyle}>
                <div style={headerStyle}>
                    <span>📊 Data Coverage</span>
                </div>
                <div style={{ padding: '12px', fontSize: '12px', color: '#dc2626' }}>
                    {error || 'No data available'}
                </div>
            </div>
        );
    }

    const gapsPercentage = Math.round((summary.places_with_gaps / summary.total_places) * 100);
    const satellitePercent = Math.round((summary.primary_access.SATELLITE / summary.total_places) * 100);

    return (
        <div style={panelStyle}>
            {/* Header */}
            <div
                style={{ ...headerStyle, cursor: onToggle ? 'pointer' : 'default' }}
                onClick={onToggle}
            >
                <span>📊 Data Coverage Layer</span>
                {onToggle && (
                    <span style={{ fontSize: '10px', marginLeft: '8px' }}>
                        {isExpanded ? '▼' : '▶'}
                    </span>
                )}
            </div>

            {/* Quick Stats */}
            <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb' }}>
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '8px',
                    fontSize: '11px'
                }}>
                    <div>
                        <div style={{ color: '#6b7280', marginBottom: '2px' }}>Total Places</div>
                        <div style={{ fontWeight: '600', fontSize: '16px', color: '#1f2937' }}>
                            {summary.total_places}
                        </div>
                    </div>
                    <div>
                        <div style={{ color: '#6b7280', marginBottom: '2px' }}>With Data Gaps</div>
                        <div style={{ fontWeight: '600', fontSize: '16px', color: '#f97316' }}>
                            {summary.places_with_gaps} <span style={{ fontSize: '11px', fontWeight: 'normal' }}>({gapsPercentage}%)</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Confidence Distribution */}
            <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb' }}>
                <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '6px', fontWeight: '600' }}>
                    Data Confidence
                </div>
                <div style={{ display: 'flex', gap: '4px', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                    <div
                        style={{
                            flex: summary.confidence_distribution.HIGH,
                            backgroundColor: getConfidenceColor('HIGH'),
                            minWidth: summary.confidence_distribution.HIGH > 0 ? '4px' : '0'
                        }}
                        title={`HIGH: ${summary.confidence_distribution.HIGH} places`}
                    />
                    <div
                        style={{
                            flex: summary.confidence_distribution.MEDIUM,
                            backgroundColor: getConfidenceColor('MEDIUM'),
                            minWidth: summary.confidence_distribution.MEDIUM > 0 ? '4px' : '0'
                        }}
                        title={`MEDIUM: ${summary.confidence_distribution.MEDIUM} places`}
                    />
                    <div
                        style={{
                            flex: summary.confidence_distribution.LOW,
                            backgroundColor: getConfidenceColor('LOW'),
                            minWidth: summary.confidence_distribution.LOW > 0 ? '4px' : '0'
                        }}
                        title={`LOW: ${summary.confidence_distribution.LOW} places`}
                    />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px', fontSize: '10px' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                        <span style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: getConfidenceColor('HIGH') }} />
                        High ({summary.confidence_distribution.HIGH})
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                        <span style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: getConfidenceColor('MEDIUM') }} />
                        Medium ({summary.confidence_distribution.MEDIUM})
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                        <span style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: getConfidenceColor('LOW') }} />
                        Low ({summary.confidence_distribution.LOW})
                    </span>
                </div>
            </div>

            {/* Primary Access Type */}
            <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb' }}>
                <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '6px', fontWeight: '600' }}>
                    Primary Internet Access
                </div>
                <div style={{ display: 'flex', gap: '8px', fontSize: '11px' }}>
                    <div style={{
                        flex: 1,
                        padding: '6px',
                        borderRadius: '4px',
                        backgroundColor: '#dbeafe',
                        textAlign: 'center'
                    }}>
                        <div style={{ fontWeight: '600', color: '#1e40af' }}>📡 {satellitePercent}%</div>
                        <div style={{ color: '#6b7280', fontSize: '10px' }}>Satellite</div>
                    </div>
                    <div style={{
                        flex: 1,
                        padding: '6px',
                        borderRadius: '4px',
                        backgroundColor: '#dcfce7',
                        textAlign: 'center'
                    }}>
                        <div style={{ fontWeight: '600', color: '#166534' }}>🔌 {100 - satellitePercent}%</div>
                        <div style={{ color: '#6b7280', fontSize: '10px' }}>Wired</div>
                    </div>
                </div>
            </div>

            {/* Expanded: Gap Breakdown */}
            {isExpanded && (
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
                                    <span>
                                        {info.icon} {info.label}
                                    </span>
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
                padding: '8px 12px',
                fontSize: '10px',
                color: '#9ca3af',
                backgroundColor: '#f9fafb',
                borderTop: '1px solid #e5e7eb'
            }}>
                Data source: FCC Broadband Availability
            </div>
        </div>
    );
}

// Styles
const panelStyle: React.CSSProperties = {
    position: 'absolute',
    bottom: '80px',
    left: '10px',
    backgroundColor: 'white',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
    zIndex: 1000,
    minWidth: '220px',
    maxWidth: '280px',
    fontSize: '13px',
    overflow: 'hidden'
};

const headerStyle: React.CSSProperties = {
    padding: '10px 12px',
    backgroundColor: '#1e40af',
    color: 'white',
    fontSize: '13px',
    fontWeight: '600',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between'
};
