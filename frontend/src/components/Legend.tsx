import React from 'react';
import { getTierColor, getTierLabel } from '../api/catApi';

interface LegendProps {
    totalRegions?: number;
}

/**
 * Map legend showing CAT tier color coding
 */
export default function Legend({ totalRegions }: LegendProps) {
    const tiers = [1, 2, 3, 4];

    return (
        <div style={{
            position: 'absolute',
            bottom: '80px',
            right: '10px',
            backgroundColor: 'white',
            padding: '12px 16px',
            borderRadius: '8px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            zIndex: 1000,
            minWidth: '180px',
            fontSize: '13px',
        }}>
            <h4 style={{
                margin: '0 0 10px 0',
                color: '#1f2937',
                fontSize: '14px',
                fontWeight: '600'
            }}>
                Community Access Tiers
            </h4>

            {tiers.map(tier => (
                <div
                    key={tier}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        marginBottom: '6px',
                        gap: '8px'
                    }}
                >
                    <div style={{
                        width: '14px',
                        height: '14px',
                        borderRadius: '50%',
                        backgroundColor: getTierColor(tier),
                        border: '2px solid white',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.2)'
                    }} />
                    <span style={{ color: '#374151', fontSize: '12px' }}>
                        <strong>Tier {tier}:</strong> {getTierLabel(tier)}
                    </span>
                </div>
            ))}

            {totalRegions !== undefined && (
                <div style={{
                    marginTop: '10px',
                    paddingTop: '8px',
                    borderTop: '1px solid #e5e7eb',
                    fontSize: '11px',
                    color: '#6b7280'
                }}>
                    Showing {totalRegions} communities
                </div>
            )}
        </div>
    );
}
