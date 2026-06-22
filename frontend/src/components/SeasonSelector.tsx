import React from 'react';

export type Season = 'summer' | 'winter' | 'year_round';

interface SeasonSelectorProps {
    season: Season;
    onChange: (season: Season) => void;
}

/**
 * Season selector dropdown for TENeT.
 * Clean dropdown design for the top-right info panel.
 */
export default function SeasonSelector({ season, onChange }: SeasonSelectorProps) {
    const getLabel = (s: Season): string => {
        switch (s) {
            case 'summer': return 'Summer';
            case 'winter': return 'Winter';
            case 'year_round': return 'Year-Round Average';
        }
    };

    return (
        <select
            aria-label="Season scenario"
            data-testid="season-selector"
            value={season}
            onChange={(e) => onChange(e.target.value as Season)}
            style={{
                padding: '8px 12px',
                fontSize: '12px',
                fontWeight: '500',
                color: '#475569',
                backgroundColor: 'white',
                border: '1px solid rgba(0, 0, 0, 0.1)',
                borderRadius: '8px',
                cursor: 'pointer',
                outline: 'none',
                appearance: 'none',
                WebkitAppearance: 'none',
                backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23475569' d='M3 4.5L6 7.5L9 4.5'/%3E%3C/svg%3E")`,
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'right 10px center',
                paddingRight: '32px',
                minWidth: '140px'
            }}
            title="Select season scenario"
        >
            <option value="summer">Summer</option>
            <option value="winter">Winter</option>
            <option value="year_round">Year-Round Average</option>
        </select>
    );
}
