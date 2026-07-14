import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import type { ButtonSize, ButtonVariant } from './Button';
import './ui.css';

export interface IconButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'aria-label'> {
    'aria-label': string;
    icon: ReactNode;
    variant?: ButtonVariant;
    size?: ButtonSize;
}

const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton({
    'aria-label': ariaLabel,
    icon,
    variant = 'ghost',
    size = 'default',
    className = '',
    type = 'button',
    ...props
}, ref) {
    const classes = ['ui-icon-button', `ui-button--${variant}`, `ui-icon-button--${size}`, className]
        .filter(Boolean)
        .join(' ');

    return (
        <button
            ref={ref}
            type={type}
            className={classes}
            aria-label={ariaLabel}
            {...props}
        >
            <span className="ui-icon-button__icon" aria-hidden="true">{icon}</span>
        </button>
    );
});

export default IconButton;
