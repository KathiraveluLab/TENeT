import type { StatusTone } from '../components/ui/StatusBadge';

export type TelehealthStatusName =
    | 'TELEHEALTH_READY'
    | 'COMMUNITY_ANCHOR'
    | 'CRITICAL_GAP'
    | 'DATA_UNAVAILABLE';

export type ScenarioTelehealthStatusName = TelehealthStatusName | 'LIMITED_TELEHEALTH';

interface TelehealthStatusPresentation {
    label: string;
    color: string;
    scenarioColor?: string;
    tone: StatusTone;
    className: string;
    description: string;
}

export const TELEHEALTH_STATUS_PRESENTATION: Record<ScenarioTelehealthStatusName, TelehealthStatusPresentation> = {
    TELEHEALTH_READY: {
        label: 'Telehealth Ready',
        color: '#22c55e',
        tone: 'ready',
        className: 'status-ready',
        description: 'Affordable home access',
    },
    COMMUNITY_ANCHOR: {
        label: 'Community Anchor',
        color: '#f59e0b',
        scenarioColor: '#f97316',
        tone: 'anchor',
        className: 'status-anchor',
        description: 'Nearby clinic safety net',
    },
    LIMITED_TELEHEALTH: {
        label: 'Limited Telehealth',
        color: '#eab308',
        tone: 'limited',
        className: 'status-limited',
        description: 'Some access requirements are not met',
    },
    CRITICAL_GAP: {
        label: 'Critical Gap',
        color: '#ef4444',
        tone: 'critical',
        className: 'status-critical',
        description: 'Unaffordable access and no nearby clinic',
    },
    DATA_UNAVAILABLE: {
        label: 'Data Unavailable',
        color: '#6b7280',
        tone: 'neutral',
        className: 'status-unknown',
        description: 'Required classification data is missing',
    },
};

export const BASE_TELEHEALTH_STATUSES: TelehealthStatusName[] = [
    'TELEHEALTH_READY',
    'COMMUNITY_ANCHOR',
    'CRITICAL_GAP',
    'DATA_UNAVAILABLE',
];

export const SCENARIO_TELEHEALTH_STATUSES: ScenarioTelehealthStatusName[] = [
    'TELEHEALTH_READY',
    'COMMUNITY_ANCHOR',
    'LIMITED_TELEHEALTH',
    'CRITICAL_GAP',
    'DATA_UNAVAILABLE',
];

export function isScenarioTelehealthStatus(value: unknown): value is ScenarioTelehealthStatusName {
    return typeof value === 'string'
        && SCENARIO_TELEHEALTH_STATUSES.includes(value as ScenarioTelehealthStatusName);
}

export function getTelehealthStatusPresentation(status: ScenarioTelehealthStatusName) {
    return TELEHEALTH_STATUS_PRESENTATION[status];
}

export function getTelehealthStatusLabel(status: ScenarioTelehealthStatusName): string {
    return getTelehealthStatusPresentation(status).label;
}

export function getTelehealthStatusColor(
    status: ScenarioTelehealthStatusName,
    context: 'baseline' | 'scenario' = 'baseline',
): string {
    const presentation = getTelehealthStatusPresentation(status);
    return context === 'scenario' ? presentation.scenarioColor ?? presentation.color : presentation.color;
}

export function getTelehealthStatusTone(status: ScenarioTelehealthStatusName): StatusTone {
    return getTelehealthStatusPresentation(status).tone;
}

export function getTelehealthStatusClassName(status: ScenarioTelehealthStatusName): string {
    return getTelehealthStatusPresentation(status).className;
}
