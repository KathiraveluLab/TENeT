/**
 * Scenario API client – POST /api/cat/scenarios/preview
 */

import type { Season } from './catApi';
import { API_BASE } from './catApi';
import type { ScenarioPreviewResponse, ScenarioThresholds } from '../types/scenario';
import { fetchJson } from './http';

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
    return fetchJson<ScenarioPreviewResponse>(`${API_BASE}/scenarios/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal,
    }, 'Scenario preview failed');
}
