import { useEffect, useId, useRef, useState } from 'react';
import {
    type DataGapsSummary,
    fetchDataGapsSummary,
} from '../api/catApi';
import { errorMessage, isAbortError } from '../api/http';
import {
    DATA_CONFIDENCE_LEVELS,
    DATA_CONFIDENCE_PRESENTATION,
    getDataGapPresentation,
} from '../domain/metrics';
import Button from './ui/Button';
import IconButton from './ui/IconButton';
import './DataCoveragePanel.css';

interface DataCoveragePanelProps {
    isExpanded?: boolean;
    onToggle?: () => void;
    totalRegions?: number;
}

export default function DataCoveragePanel({
    isExpanded = false,
    onToggle,
}: DataCoveragePanelProps) {
    const [summary, setSummary] = useState<DataGapsSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [open, setOpen] = useState(false);
    const shellRef = useRef<HTMLDivElement>(null);
    const triggerRef = useRef<HTMLButtonElement>(null);
    const panelId = useId();

    useEffect(() => {
        const controller = new AbortController();
        async function loadData() {
            try {
                setLoading(true);
                const data = await fetchDataGapsSummary(controller.signal);
                setSummary(data);
                setError(null);
            } catch (caught: unknown) {
                if (!isAbortError(caught)) {
                    setError(errorMessage(caught, 'Failed to load data gaps'));
                }
            } finally {
                if (!controller.signal.aborted) setLoading(false);
            }
        }
        loadData();
        return () => controller.abort();
    }, []);

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

    const close = () => {
        setOpen(false);
        triggerRef.current?.focus();
    };

    const totalPlaces = summary?.total_places ?? 0;
    const gapsPercentage = summary && summary.total_places > 0
        ? Math.round((summary.places_with_gaps / summary.total_places) * 100)
        : 0;
    const satellitePercent = summary && summary.total_places > 0
        ? Math.round(((summary.primary_access.SATELLITE ?? 0) / summary.total_places) * 100)
        : null;

    return (
        <div ref={shellRef} className="data-coverage-popover">
            <Button
                ref={triggerRef}
                size="small"
                className="data-coverage-trigger"
                aria-label={open ? 'Close data coverage summary' : 'Open data coverage summary'}
                aria-expanded={open}
                aria-controls={panelId}
                onClick={() => setOpen(value => !value)}
            >
                Data coverage
            </Button>

            <div
                id={panelId}
                className="data-coverage-panel"
                role="region"
                aria-label="Data coverage summary"
                hidden={!open}
            >
                <div className="data-coverage-header">
                    <div>
                        <h4>Data Coverage</h4>
                        <span>Availability and confidence</span>
                    </div>
                    <IconButton
                        icon="×"
                        size="small"
                        aria-label="Close data coverage summary"
                        onClick={close}
                    />
                </div>

                {loading && <div className="data-coverage-state" role="status">Loading coverage data…</div>}

                {!loading && (error || !summary) && (
                    <div className="data-coverage-state data-coverage-state--error" role="alert">
                        {error || 'No data available'}
                    </div>
                )}

                {!loading && summary && (
                    <>
                        <div className="data-coverage-stats">
                            <div>
                                <span>Broadband places</span>
                                <strong>{totalPlaces}</strong>
                            </div>
                            <div className="data-coverage-stat--alert">
                                <span>With data gaps</span>
                                <strong>{summary.places_with_gaps}</strong>
                                <small>{gapsPercentage}% of total</small>
                            </div>
                        </div>

                        <section className="data-coverage-section">
                            <h5>Data confidence</h5>
                            <div className="data-coverage-distribution" aria-label="Data confidence distribution">
                                {DATA_CONFIDENCE_LEVELS.map(level => {
                                    const count = summary.confidence_distribution[level];
                                    const presentation = DATA_CONFIDENCE_PRESENTATION[level];
                                    return (
                                        <span
                                            key={level}
                                            className={presentation.className}
                                            style={{ flex: count, display: count > 0 ? undefined : 'none' }}
                                            title={`${count} ${presentation.label.toLowerCase()}-confidence places`}
                                        />
                                    );
                                })}
                            </div>
                            <div className="data-coverage-key">
                                {DATA_CONFIDENCE_LEVELS.map(level => {
                                    const presentation = DATA_CONFIDENCE_PRESENTATION[level];
                                    return (
                                        <span key={level}>
                                            <i className={presentation.className} />
                                            {presentation.label} {summary.confidence_distribution[level]}
                                        </span>
                                    );
                                })}
                            </div>
                        </section>

                        <section className="data-coverage-section">
                            <h5>Primary internet access</h5>
                            <div className="data-coverage-access">
                                <div><strong>{satellitePercent === null ? '—' : `${satellitePercent}%`}</strong><span>Satellite</span></div>
                                <div><strong>{satellitePercent === null ? '—' : `${100 - satellitePercent}%`}</strong><span>Wired or other</span></div>
                            </div>
                        </section>

                        {(isExpanded || !onToggle) && (
                            <section className="data-coverage-section">
                                <h5>Most common gap types</h5>
                                <div className="data-coverage-gaps">
                                    {Object.entries(summary.gap_breakdown)
                                        .filter(([, data]) => data.count > 0)
                                        .sort(([, a], [, b]) => b.count - a.count)
                                        .slice(0, 5)
                                        .map(([gapType, data]) => {
                                            const info = getDataGapPresentation(gapType);
                                            return (
                                                <div key={gapType}>
                                                    <span>{info.label}</span>
                                                    <strong className={`is-${info.severity}`}>
                                                        {data.count} ({data.percentage}%)
                                                    </strong>
                                                </div>
                                            );
                                        })}
                                </div>
                            </section>
                        )}

                        {onToggle && (
                            <Button size="small" variant="ghost" onClick={onToggle}>
                                {isExpanded ? 'Show less detail' : 'Show more detail'}
                            </Button>
                        )}

                        <div className="data-coverage-source">Source: FCC Broadband Availability</div>
                    </>
                )}
            </div>
        </div>
    );
}
