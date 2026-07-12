import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import './ui.css';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'small' | 'default';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: ButtonVariant;
    size?: ButtonSize;
    leadingIcon?: ReactNode;
    trailingIcon?: ReactNode;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button({
    variant = 'secondary',
    size = 'default',
    leadingIcon,
    trailingIcon,
    className = '',
    children,
    type = 'button',
    ...props
}, ref) {
    const classes = ['ui-button', `ui-button--${variant}`, `ui-button--${size}`, className]
        .filter(Boolean)
        .join(' ');

    return (
        <button ref={ref} type={type} className={classes} {...props}>
            {leadingIcon && <span className="ui-button__icon" aria-hidden="true">{leadingIcon}</span>}
            <span className="ui-button__label">{children}</span>
            {trailingIcon && <span className="ui-button__icon" aria-hidden="true">{trailingIcon}</span>}
        </button>
    );
});

export default Button;
