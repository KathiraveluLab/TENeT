import { useCallback, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import './MetricTooltip.css';

interface MetricTooltipProps {
    term: string;
    children: string;
}

export default function MetricTooltip({ term, children }: MetricTooltipProps) {
    const triggerRef = useRef<HTMLButtonElement | null>(null);
    const [open, setOpen] = useState(false);
    const [placement, setPlacement] = useState<'above' | 'below'>('above');
    const [position, setPosition] = useState({ top: 0, left: 0 });

    const updatePosition = useCallback(() => {
        const trigger = triggerRef.current;
        if (!trigger) return;

        const rect = trigger.getBoundingClientRect();
        const panelWidth = Math.min(260, window.innerWidth - 24);
        const left = Math.min(
            Math.max(rect.left + rect.width / 2 - panelWidth / 2, 12),
            window.innerWidth - panelWidth - 12,
        );
        const hasRoomAbove = rect.top > 136;

        setPlacement(hasRoomAbove ? 'above' : 'below');
        setPosition({
            left,
            top: hasRoomAbove ? rect.top - 8 : rect.bottom + 8,
        });
    }, []);

    const showTooltip = () => {
        updatePosition();
        setOpen(true);
    };

    useLayoutEffect(() => {
        if (!open) return;
        updatePosition();
        window.addEventListener('resize', updatePosition);
        window.addEventListener('scroll', updatePosition, true);

        return () => {
            window.removeEventListener('resize', updatePosition);
            window.removeEventListener('scroll', updatePosition, true);
        };
    }, [open, updatePosition]);

    const tooltipPanel = open
        ? createPortal(
            <span
                className={`metric-tooltip-panel ${placement}`}
                role="tooltip"
                style={position}
            >
                <strong>{term}</strong>
                <span>{children}</span>
            </span>,
            document.body,
        )
        : null;

    return (
        <span
            className="metric-tooltip"
            onMouseEnter={showTooltip}
            onMouseLeave={() => setOpen(false)}
        >
            <button
                ref={triggerRef}
                type="button"
                className="metric-tooltip-trigger"
                aria-label={`${term}: ${children}`}
                onFocus={showTooltip}
                onBlur={() => setOpen(false)}
            >
                i
            </button>
            {tooltipPanel}
        </span>
    );
}
