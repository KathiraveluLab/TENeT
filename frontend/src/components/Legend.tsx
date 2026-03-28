import React from 'react';
import { getNeedColor, getNeedLabel } from '../api/catApi';

interface LegendProps {
    totalRegions?: number;
}

// Helper for need description
const getNeedCapability = (score: number): string => {
    if (score >= 75) return 'Severe lack of nearby healthcare facilities';
    if (score >= 50) return 'Limited access to clinics or hospitals';
    if (score >= 25) return 'Adequate access with some travel distance';
    return 'Good access to nearby healthcare facilities';
};

/**
 * Map legend showing CAT tier color coding
 */
export default function Legend({ totalRegions }: LegendProps) {
    const needLevels = [87, 62, 37, 12];

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
                    Telehealth Need
                </h4>
                <span style={{ fontSize: '10px', color: '#64748b', fontWeight: '500' }}>Score (0-100)</span>
            </div>

            {needLevels.map(score => (
                <div
                    key={score}
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
                        backgroundColor: getNeedColor(score),
                        flexShrink: 0,
                        marginTop: '3px',
                        boxShadow: '0 1px 2px rgba(0,0,0,0.15)'
                    }} />
                    <div>
                        <div style={{ color: '#1e293b', fontWeight: '500' }}>
                            {getNeedLabel(score)}
                        </div>
                        <div style={{ color: '#64748b', fontSize: '10px' }}>
                            {getNeedCapability(score)}
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

            {/* Color scale indicator */}
            <div style={{
                marginTop: '10px',
                paddingTop: '8px',
                borderTop: '1px solid #e5e7eb',
            }}>
                <div style={{
                    height: '6px',
                    borderRadius: '3px',
                    background: `linear-gradient(to right, ${getNeedColor(12)}, ${getNeedColor(37)}, ${getNeedColor(62)}, ${getNeedColor(87)})`,
                    marginBottom: '4px',
                }} />
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: '9px',
                    color: '#94a3b8',
                }}>
                    <span>Low Need</span>
                    <span>High Need</span>
                </div>
            </div>
        </div>
    );
}

