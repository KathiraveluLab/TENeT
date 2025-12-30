import React from 'react';

export type Season = 'summer' | 'winter' | 'year_round';

interface SeasonSelectorProps {
    season: Season;
    onChange: (season: Season) => void;
}

/**
 * Season selector toggle for TENeT.
 * User-selected season controls transport difficulty assumptions in API queries.
 */
export default function SeasonSelector({ season, onChange }: SeasonSelectorProps) {
    const seasons: { id: Season; label: string; icon: string }[] = [
        { id: 'summer', label: 'Summer', icon: '☀️' },
        { id: 'winter', label: 'Winter', icon: '❄️' },
        { id: 'year_round', label: 'Year-Round', icon: '📅' },
    ];

    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
            borderRadius: '8px',
        }}>
            <span style={{
                fontSize: '13px',
                fontWeight: '500',
                color: 'rgba(255, 255, 255, 0.8)',
                marginRight: '4px',
            }}>
                Season Scenario:
            </span>

            {seasons.map(({ id, label, icon }) => (
                <button
                    key={id}
                    onClick={() => onChange(id)}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: '6px 12px',
                        fontSize: '13px',
                        fontWeight: season === id ? '600' : '400',
                        color: season === id ? '#1e40af' : 'white',
                        backgroundColor: season === id ? 'white' : 'transparent',
                        border: season === id ? 'none' : '1px solid rgba(255, 255, 255, 0.3)',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                    }}
                    onMouseOver={(e) => {
                        if (season !== id) {
                            e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.15)';
                        }
                    }}
                    onMouseOut={(e) => {
                        if (season !== id) {
                            e.currentTarget.style.backgroundColor = 'transparent';
                        }
                    }}
                    aria-pressed={season === id}
                    title={`Set season scenario to ${label}`}
                >
                    <span style={{ fontSize: '14px' }}>{icon}</span>
                    <span>{label}</span>
                </button>
            ))}
        </div>
    );
}
