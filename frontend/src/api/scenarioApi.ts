/**
 * Scenario API client – POST /api/cat/scenarios/preview
 */

import type { Season } from './catApi';
import { API_BASE } from './catApi';
import type { ScenarioPreviewResponse, ScenarioThresholds } from '../types/scenario';

export interface ScenarioPreviewRequest {
    mode: 'preview';
    season: Season;
    thresholds: ScenarioThresholds;
    region_codes: string[] | null;
}

/**
 * Fetch a scenario preview from the backend.
 *
 * Supports `AbortSignal` so callers can cancel stale requests.
 */
export async function fetchScenarioPreview(
    request: ScenarioPreviewRequest,
    signal?: AbortSignal,
): Promise<ScenarioPreviewResponse> {
    const response = await fetch(`${API_BASE}/scenarios/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal,
    });

    if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        throw new Error(errorBody.error || `Scenario preview failed: ${response.statusText}`);
    }

    return response.json();
}
