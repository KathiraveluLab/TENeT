import type { Season } from '../../api/catApi';
import SeasonSelector from '../SeasonSelector';
import Button from '../ui/Button';
import './MapToolbar.css';

interface MapToolbarProps {
    season: Season;
    scenarioActive: boolean;
    scenarioDisabled?: boolean;
    onSeasonChange: (season: Season) => void;
    onOpenInsights: () => void;
    onToggleScenario: () => void;
}

export default function MapToolbar({
    season,
    scenarioActive,
    scenarioDisabled = false,
    onSeasonChange,
    onOpenInsights,
    onToggleScenario,
}: MapToolbarProps) {
    return (
        <header className="map-toolbar" aria-label="Map tools">
            <div className="map-toolbar__brand">
                <strong>TENeT</strong>
                <span>Telehealth effectiveness and Necessity Tracker</span>
            </div>

            <div className="map-toolbar__divider" aria-hidden="true" />

            <div className="map-toolbar__controls">
                <div className="map-toolbar__season">
                    <span className="map-toolbar__control-label">Season</span>
                    <SeasonSelector season={season} onChange={onSeasonChange} />
                </div>

                <Button
                    id="insights-toolbar-button"
                    size="small"
                    onClick={onOpenInsights}
                    aria-label="Open Statewide Insights"
                >
                    Insights
                </Button>

                <Button
                    id="scenario-toggle-button"
                    data-testid="scenario-button"
                    size="small"
                    variant={scenarioActive ? 'primary' : 'secondary'}
                    className={`map-toolbar__scenario-button${scenarioActive ? ' is-active' : ''}`}
                    onClick={onToggleScenario}
                    disabled={scenarioDisabled}
                    aria-label={scenarioActive ? 'Exit scenario mode' : 'Open what-if scenario mode'}
                    aria-pressed={scenarioActive}
                    aria-expanded={scenarioActive}
                    aria-controls="scenario-panel"
                >
                    {scenarioActive ? 'Scenario active' : 'Scenario'}
                </Button>
            </div>
        </header>
    );
}
