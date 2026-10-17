import { forwardRef, type HTMLAttributes } from 'react';
import './ui.css';

export type PanelPadding = 'none' | 'small' | 'default';

export interface PanelProps extends HTMLAttributes<HTMLDivElement> {
    padding?: PanelPadding;
    elevated?: boolean;
}

const Panel = forwardRef<HTMLDivElement, PanelProps>(function Panel({
    padding = 'default',
    elevated = false,
    className = '',
    ...props
}, ref) {
    const classes = [
        'ui-panel',
        `ui-panel--padding-${padding}`,
        elevated ? 'ui-panel--elevated' : '',
        className,
    ].filter(Boolean).join(' ');

    return <div ref={ref} className={classes} {...props} />;
});

export default Panel;
