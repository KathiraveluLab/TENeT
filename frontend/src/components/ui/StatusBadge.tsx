import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import './ui.css';

export type StatusTone = 'neutral' | 'ready' | 'anchor' | 'limited' | 'critical' | 'info';

export interface StatusBadgeProps extends HTMLAttributes<HTMLSpanElement> {
    children: ReactNode;
    tone?: StatusTone;
    showDot?: boolean;
}

const StatusBadge = forwardRef<HTMLSpanElement, StatusBadgeProps>(function StatusBadge({
    children,
    tone = 'neutral',
    showDot = false,
    className = '',
    ...props
}, ref) {
    const classes = ['ui-status-badge', `ui-status-badge--${tone}`, className]
        .filter(Boolean)
        .join(' ');

    return (
        <span ref={ref} className={classes} {...props}>
            {showDot && <span className="ui-status-badge__dot" aria-hidden="true" />}
            {children}
        </span>
    );
});

export default StatusBadge;
