import { describe, expect, it, vi } from 'vitest';
import { ResearchProfile } from '../types/research';
import { DATA_UNAVAILABLE } from './formatResearchValue';
import { exportResearchProfileReport } from './reportExport';

const {
    textCalls,
    saveMock,
    addImageMock,
    addPageMock,
    setPageMock,
    splitTextMock,
    html2canvasMock,
} = vi.hoisted(() => ({
    textCalls: [] as string[],
    saveMock: vi.fn(),
    addImageMock: vi.fn(),
    addPageMock: vi.fn(),
    setPageMock: vi.fn(),
    splitTextMock: vi.fn((value: string | string[]) => Array.isArray(value) ? value : [String(value)]),
    html2canvasMock: vi.fn(),
}));

vi.mock('html2canvas', () => ({
    default: html2canvasMock,
}));

vi.mock('jspdf', () => {
    return {
        default: vi.fn().mockImplementation(() => ({
            addImage: addImageMock,
            addPage: addPageMock,
            getNumberOfPages: vi.fn(() => addPageMock.mock.calls.length + 1),
            line: vi.fn(),
            rect: vi.fn(),
            roundedRect: vi.fn(),
            save: saveMock,
            setPage: setPageMock,
            setDrawColor: vi.fn(),
            setFillColor: vi.fn(),
            setFont: vi.fn(),
            setFontSize: vi.fn(),
            setLineWidth: vi.fn(),
            setTextColor: vi.fn(),
            splitTextToSize: splitTextMock,
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
            population: null,
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
        addPageMock.mockClear();
        html2canvasMock.mockClear();

        await exportResearchProfileReport(profileWithMissingData(), null);

        expect(textCalls).toContain(DATA_UNAVAILABLE);
        expect(textCalls).toContain('Map snapshot unavailable');
        expect(textCalls.join('\n')).not.toMatch(/\b(undefined|null|NaN)\b/);
        expect(saveMock).toHaveBeenCalledWith('tenet-community-report-missing-data-village.pdf');
    });

    it('captures the supplied map element for the location section', async () => {
        const mapElement = document.createElement('div');
        html2canvasMock.mockResolvedValueOnce({
            width: 800,
            height: 400,
            toDataURL: () => 'data:image/png;base64,map-snapshot',
        });

        await exportResearchProfileReport(profileWithMissingData(), mapElement);

        expect(html2canvasMock).toHaveBeenCalledWith(mapElement, expect.objectContaining({
            useCORS: true,
        }));
        expect(addImageMock).toHaveBeenCalledWith(
            'data:image/png;base64,map-snapshot',
            'PNG',
            expect.any(Number),
            expect.any(Number),
            expect.any(Number),
            expect.any(Number),
        );
    });

    it('adds continuation pages when report fields wrap beyond the footer boundary', async () => {
        addPageMock.mockClear();
        splitTextMock.mockImplementation((value: string | string[], width?: number) => {
            if (Array.isArray(value)) return value;
            const text = String(value);
            const chunkSize = Math.max(8, Math.floor(Number(width || 30)));
            return text.match(new RegExp(`.{1,${chunkSize}}`, 'g')) ?? [''];
        });
        const profile = profileWithMissingData();
        profile.methodology.confidence_notes = ['Long source note '.repeat(120)];
        profile.methodology.sources = ['Long methodology source '.repeat(80)];

        await exportResearchProfileReport(profile, null);

        expect(addPageMock).toHaveBeenCalled();
        expect(setPageMock).toHaveBeenCalled();
        expect(textCalls.some(text => text.includes('Page 1 of'))).toBe(true);
        splitTextMock.mockImplementation(
            (value: string | string[]) => Array.isArray(value) ? value : [String(value)],
        );
    });
});
