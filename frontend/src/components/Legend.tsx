import { useEffect, useId, useRef, useState } from 'react';
import {
    CAT_TIERS,
    CAT_TIER_PRESENTATION,
    getDesertScorePresentation,
} from '../domain/metrics';
import MetricTooltip from './MetricTooltip';
import Button from './ui/Button';
import IconButton from './ui/IconButton';
import './Legend.css';

interface LegendProps {
    totalRegions?: number;
    position?: 'bottom-right' | 'bottom-left';
}

export default function Legend({ totalRegions, position = 'bottom-right' }: LegendProps) {
    const needLevels = [87, 62, 37, 12];
    const [open, setOpen] = useState(false);
    const shellRef = useRef<HTMLDivElement>(null);
    const triggerRef = useRef<HTMLButtonElement>(null);
    const panelId = useId();

    useEffect(() => {
        if (!open) return;

        const handlePointerDown = (event: PointerEvent) => {
            if (!shellRef.current?.contains(event.target as Node)) setOpen(false);
        };
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key !== 'Escape') return;
            setOpen(false);
            triggerRef.current?.focus();
        };

        document.addEventListener('pointerdown', handlePointerDown);
        document.addEventListener('keydown', handleKeyDown);
        return () => {
            document.removeEventListener('pointerdown', handlePointerDown);
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, [open]);

    return (
        <div
            ref={shellRef}
            className={`legend-popover ${position === 'bottom-left' ? 'legend-popover--left' : ''}`}
        >
            <Button
                ref={triggerRef}
                size="small"
                className="legend-trigger"
                aria-label={open ? 'Close discovery legend' : 'Open discovery legend'}
                aria-expanded={open}
                aria-controls={panelId}
                onClick={() => setOpen(value => !value)}
            >
                Legend
            </Button>

            <div
                id={panelId}
                className="legend-panel"
                role="region"
                aria-label="Discovery legend"
                hidden={!open}
            >
                <div className="legend-header">
                    <div>
                        <h4>Discovery Legend</h4>
                        <span>Plain-language guide</span>
                    </div>
                    <IconButton
                        icon="×"
                        size="small"
                        aria-label="Close discovery legend"
                        onClick={() => {
                            setOpen(false);
                            triggerRef.current?.focus();
                        }}
                    />
                </div>

                <div className="legend-section-title">
                    Healthcare Desert Score
                    <MetricTooltip term="Healthcare Desert Score">
                        A 0-100 need score. Higher means the community has farther or weaker access to nearby healthcare.
                    </MetricTooltip>
                </div>

                {needLevels.map(score => {
                    const presentation = getDesertScorePresentation(score);
                    return (
                        <div key={score} className="legend-row">
                            <span
                                className="legend-dot"
                                style={{ backgroundColor: presentation.color }}
                                aria-hidden="true"
                            />
                            <div>
                                <div className="legend-row-label">{presentation.label}</div>
                                <div className="legend-row-note">{presentation.description}</div>
                            </div>
                        </div>
                    );
                })}

                <div className="legend-section">
                    <div className="legend-section-title">
                        CAT Tiers
                        <MetricTooltip term="CAT Tier">
                            Community Access Tier summarizes how isolated a community is for practical care access and transport.
                        </MetricTooltip>
                    </div>
                    <div className="legend-tier-list">
                        {CAT_TIERS.map(tier => (
                            <div key={tier}>
                                <strong>Tier {tier}:</strong> {CAT_TIER_PRESENTATION[tier].shortDescription}
                            </div>
                        ))}
                    </div>
                </div>

                {totalRegions !== undefined && (
                    <div className="legend-footer-row">
                        <span>Communities</span>
                        <strong>{totalRegions}</strong>
                    </div>
                )}

                <div className="legend-scale">
                    <div
                        className="legend-gradient"
                        style={{
                            background: `linear-gradient(to right, ${needLevels.slice().reverse().map(score => getDesertScorePresentation(score).color).join(', ')})`,
                        }}
                    />
                    <div className="legend-scale-labels">
                        <span>Low Need</span>
                        <span>High Need</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
