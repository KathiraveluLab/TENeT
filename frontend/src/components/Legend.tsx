import React from 'react';
import { getTierColor, getTierLabel } from '../api/catApi';

interface LegendProps {
    totalRegions?: number;
}

// Helper for tier description
const getTierCapability = (tier: number): string => {
    switch (tier) {
        case 1: return 'HD Video Ready';
        case 2: return 'Video Capable';
        case 3: return 'Audio Only';
        case 4: return 'Async/Text Only';
        default: return '';
    }
};

/**
 * Map legend showing CAT tier color coding
 */
export default function Legend({ totalRegions }: LegendProps) {
    const tiers = [1, 2, 3, 4];

    return (
        <div style={{
            position: 'absolute',
            bottom: '80px',
            right: '20px',
            zIndex: 1000,
            minWidth: '220px',
            // Glassmorphism
            background: 'rgba(255, 255, 255, 0.92)',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            padding: '16px 18px',
            borderRadius: '12px',
            border: '1px solid rgba(255, 255, 255, 0.3)',
            boxShadow: '0 8px 32px rgba(31, 38, 135, 0.12)',
            fontSize: '12px',
        }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '12px',
                paddingBottom: '10px',
                borderBottom: '1px solid rgba(0, 0, 0, 0.08)'
            }}>
                <h4 style={{
                    margin: 0,
                    color: '#0f172a',
                    fontSize: '14px',
                    fontWeight: '700',
                    letterSpacing: '-0.02em'
                }}>
                    Community Access Tiers
                </h4>
                <span style={{ fontSize: '10px', color: '#64748b', fontWeight: '500' }}>CAT-4</span>
            </div>

            {tiers.map(tier => (
                <div
                    key={tier}
                    style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        marginBottom: '8px',
                        gap: '10px'
                    }}
                >
                    <div style={{
                        width: '12px',
                        height: '12px',
                        borderRadius: '50%',
                        backgroundColor: getTierColor(tier),
                        flexShrink: 0,
                        marginTop: '3px',
                        boxShadow: '0 1px 2px rgba(0,0,0,0.15)'
                    }} />
                    <div>
                        <div style={{ color: '#1e293b', fontWeight: '500' }}>
                            Tier {tier}: {getTierLabel(tier)}
                        </div>
                        <div style={{ color: '#64748b', fontSize: '10px' }}>
                            {getTierCapability(tier)}
                        </div>
                    </div>
                </div>
            ))}

            {totalRegions !== undefined && (
                <div style={{
                    marginTop: '10px',
                    paddingTop: '8px',
                    borderTop: '1px solid #e5e7eb',
                    fontSize: '10px',
                    color: '#64748b',
                    display: 'flex',
                    justifyContent: 'space-between'
                }}>
                    <span>Communities</span>
                    <strong style={{ color: '#334155' }}>{totalRegions}</strong>
                </div>
            )}
        </div>
    );
}

