/**
 * Shared traffic-light scoring utilities used by PerformanceLayer and ChoroplethLayer.
 */

export const CRITICAL_LATENCY_MS = 150;
export const CRITICAL_SPEED_MBPS = 5;
export const AFFORDABILITY_BURDEN_THRESHOLD = 2.0;

export function getScenarioCost(lat: number, useStarlink: boolean): number {
    if (useStarlink) return 120;
    return lat > 63 ? 450 : 125;
}

export function getTrafficLightStatus(
    speed: number,
    latency: number,
    burden: number | null,
    scenarioCost: number,
): 'GREEN' | 'YELLOW' | 'ORANGE' | 'RED' | 'GRAY' {
    const isRuralTier = scenarioCost >= 400;

    if (latency > CRITICAL_LATENCY_MS || speed < CRITICAL_SPEED_MBPS) {
        return 'RED';
    }
    if (burden !== null && burden > AFFORDABILITY_BURDEN_THRESHOLD) {
        return 'RED';
    }
    if (isRuralTier) {
        return 'ORANGE';
    }
    if (latency > 50 && latency <= CRITICAL_LATENCY_MS) {
        return 'YELLOW';
    }
    if (speed < 25) {
        return 'YELLOW';
    }
    if (latency <= 50 && (burden === null || burden <= AFFORDABILITY_BURDEN_THRESHOLD) && speed >= 25) {
        return 'GREEN';
    }
    return 'GRAY';
}
