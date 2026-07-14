import type { Season } from '../api/catApi';
import './SeasonSelector.css';

interface SeasonSelectorProps {
    season: Season;
    onChange: (season: Season) => void;
}

export default function SeasonSelector({ season, onChange }: SeasonSelectorProps) {
    return (
        <select
            className="season-selector"
            aria-label="Season scenario"
            data-testid="season-selector"
            value={season}
            onChange={(e) => onChange(e.target.value as Season)}
            title="Select season scenario"
        >
            <option value="summer">Summer</option>
            <option value="winter">Winter</option>
            <option value="year_round">Year-Round Average</option>
        </select>
    );
}
