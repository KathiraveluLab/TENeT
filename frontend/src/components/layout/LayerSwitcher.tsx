import './LayerSwitcher.css';
import type { BaseMapLayer } from '../../domain/mapMode';

export type { BaseMapLayer } from '../../domain/mapMode';

interface LayerSwitcherProps {
    activeLayer: BaseMapLayer;
    scenarioActive?: boolean;
    onChange: (layer: BaseMapLayer) => void;
}

const LAYERS: Array<{ id: BaseMapLayer; label: string }> = [
    { id: 'cat', label: 'CAT' },
    { id: 'gap', label: 'Gap Hunter' },
    { id: 'affordability', label: 'Affordability' },
];

export default function LayerSwitcher({
    activeLayer,
    scenarioActive = false,
    onChange,
}: LayerSwitcherProps) {
    return (
        <section className="layer-switcher" aria-label="Map layers">
            <div className="layer-switcher__header">
                <span>Layer</span>
                {scenarioActive && <strong>Scenario active</strong>}
            </div>
            <div className="layer-switcher__options" role="group" aria-label="Select map layer">
                {LAYERS.map(layer => {
                    const active = !scenarioActive && activeLayer === layer.id;
                    return (
                        <button
                            key={layer.id}
                            type="button"
                            className={`layer-switcher__option${active ? ' is-active' : ''}`}
                            aria-pressed={active}
                            aria-label={`Map layer: ${layer.label}`}
                            onClick={() => onChange(layer.id)}
                        >
                            {layer.label}
                        </button>
                    );
                })}
            </div>
        </section>
    );
}
