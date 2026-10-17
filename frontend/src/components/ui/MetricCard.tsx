import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import './ui.css';

export type MetricTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info';

export interface MetricCardProps extends HTMLAttributes<HTMLElement> {
    label: string;
    value: ReactNode;
    supportingText?: ReactNode;
    tone?: MetricTone;
}

const MetricCard = forwardRef<HTMLElement, MetricCardProps>(function MetricCard({
    label,
    value,
    supportingText,
    tone = 'neutral',
    className = '',
    ...props
}, ref) {
    const classes = ['ui-metric-card', `ui-metric-card--${tone}`, className]
        .filter(Boolean)
        .join(' ');

    return (
        <article ref={ref} className={classes} {...props}>
            <span className="ui-metric-card__label">{label}</span>
            <strong className="ui-metric-card__value">{value}</strong>
            {supportingText && (
                <span className="ui-metric-card__supporting-text">{supportingText}</span>
            )}
        </article>
    );
});

export default MetricCard;
