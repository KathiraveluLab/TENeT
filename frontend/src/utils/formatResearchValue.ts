import { formatStatus } from '../components/sidebar/sidebarUtils';

export const DATA_UNAVAILABLE = 'Data unavailable';

export function formatResearchValue(
    value: number | string | boolean | null | undefined,
    options: {
        suffix?: string;
        prefix?: string;
        digits?: number;
        booleanLabels?: [string, string];
    } = {},
): string {
    if (value === null || value === undefined || value === '') {
        return DATA_UNAVAILABLE;
    }

    if (typeof value === 'boolean') {
        const labels = options.booleanLabels ?? ['Yes', 'No'];
        return value ? labels[0] : labels[1];
    }

    if (typeof value === 'number') {
        if (!Number.isFinite(value)) {
            return DATA_UNAVAILABLE;
        }
        const digits = options.digits ?? (Number.isInteger(value) ? 0 : 1);
        return `${options.prefix ?? ''}${value.toLocaleString(undefined, {
            maximumFractionDigits: digits,
            minimumFractionDigits: 0,
        })}${options.suffix ?? ''}`;
    }

    return value;
}

export function formatStatusText(value: string | null | undefined): string {
    return formatStatus(value, DATA_UNAVAILABLE);
}
