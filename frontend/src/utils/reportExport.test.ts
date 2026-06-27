import { describe, expect, it, vi } from 'vitest';
import { ResearchProfile } from '../types/research';
import { DATA_UNAVAILABLE } from './formatResearchValue';
import { exportResearchProfileReport } from './reportExport';

const textCalls: string[] = [];
const saveMock = vi.fn();

vi.mock('jspdf', () => {
    return {
        default: vi.fn().mockImplementation(() => ({
            addPage: vi.fn(),
            line: vi.fn(),
            rect: vi.fn(),
            roundedRect: vi.fn(),
            save: saveMock,
            setDrawColor: vi.fn(),
            setFillColor: vi.fn(),
            setFont: vi.fn(),
            setFontSize: vi.fn(),
            setLineWidth: vi.fn(),
            setTextColor: vi.fn(),
            splitTextToSize: vi.fn((value: string | string[]) => Array.isArray(value) ? value : [String(value)]),
            getTextWidth: vi.fn((value: string) => String(value).length),
            text: vi.fn((value: string | string[]) => {
                if (Array.isArray(value)) {
                    textCalls.push(...value.map(String));
                } else {
                    textCalls.push(String(value));
                }
            }),
        })),
    };
});

function profileWithMissingData(): ResearchProfile {
    return {
        region: {
            region_code: 'AK-MISSING',
            name: 'Missing Data Village',
            lat: null,
            lon: null,
            cat_tier: null,
            region: null,
            has_data_gap: true,
            missing_fields: ['ookla_download_mbps', 'median_income'],
            data_confidence: 'LOW',
        },
        connectivity: {
            fcc_coverage_25mbps_pct: null,
            ookla_download_mbps: null,
            ookla_upload_mbps: null,
            latency_ms: null,
            reliability_label: null,
            isp_name: null,
            data_source: null,
        },
        affordability: {
            monthly_cost: null,
            median_income: null,
            burden_pct: null,
            threshold_pct: 2,
            status: 'unknown',
        },
        healthcare: {
            nearest_facility_name: null,
            nearest_facility_type: null,
            nearest_facility_distance_km: null,
            emergency_services: null,
            specialist_available: null,
            facility_count: null,
            desert_score: null,
        },
        telehealth: {
            status: 'DATA_UNAVAILABLE',
            label: 'Data unavailable',
            video_feasible: null,
            audio_feasible: null,
            clinic_supported: null,
            season: 'year_round',
            season_note: DATA_UNAVAILABLE,
        },
        methodology: {
            generated_at: '2026-06-11T00:00:00.000Z',
            sources: [],
            confidence_notes: [],
        },
    };
}

describe('report export missing data handling', () => {
    it('uses readable missing-data labels instead of blank/null/undefined fields', async () => {
        textCalls.length = 0;
        saveMock.mockClear();

        await exportResearchProfileReport(profileWithMissingData(), null);

        expect(textCalls).toContain(DATA_UNAVAILABLE);
        expect(textCalls.join('\n')).not.toMatch(/\b(undefined|null|NaN)\b/);
        expect(saveMock).toHaveBeenCalledWith('tenet-community-report-missing-data-village.pdf');
    });
});
