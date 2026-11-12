import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchDataGapsSummary, type DataGapsSummary } from '../api/catApi';
import DataCoveragePanel from './DataCoveragePanel';

vi.mock('../api/catApi', async () => {
    const actual = await vi.importActual<typeof import('../api/catApi')>('../api/catApi');
    return {
        ...actual,
        fetchDataGapsSummary: vi.fn(),
    };
});

const baseSummary: DataGapsSummary = {
    total_places: 294,
    places_with_gaps: 42,
    gap_breakdown: {
        MISSING_WIRED_DATA: {
            count: 25,
            percentage: 8.5,
            places: [],
        },
    },
    confidence_distribution: { HIGH: 210, MEDIUM: 42, LOW: 42 },
    telehealth_viability: { YES: 220, NO: 30, UNCERTAIN: 44 },
    primary_access: { WIRED: 180, SATELLITE: 94, LIMITED: 20 },
};

describe('DataCoveragePanel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders 4-dataset join completeness metrics when provided by backend', async () => {
        vi.mocked(fetchDataGapsSummary).mockResolvedValue({
            ...baseSummary,
            dataset_coverage: {
                total_communities: 421,
                fcc_broadband: { matched: 294, pct: 69.8 },
                ookla_performance: { matched: 380, pct: 90.3, window_km: 75 },
                acs_income: { matched: 415, pct: 98.6, window_km: 55 },
                healthcare_sites: { linked: 203, pct: 48.2 },
            },
        });

        render(<DataCoveragePanel isExpanded={true} />);
        fireEvent.click(screen.getByRole('button', { name: 'Open data coverage summary' }));

        expect(await screen.findByText('Dataset join completeness (421)')).toBeInTheDocument();
        expect(screen.getByText('FCC broadband')).toBeInTheDocument();
        expect(screen.getByText('294 (69.8%)')).toBeInTheDocument();
        expect(screen.getByText('380 (90.3%)')).toBeInTheDocument();
        expect(screen.getByText('415 (98.6%)')).toBeInTheDocument();
        expect(screen.getByText('203 (48.2%)')).toBeInTheDocument();
    });

    it('remains backward compatible when dataset_coverage is omitted', async () => {
        vi.mocked(fetchDataGapsSummary).mockResolvedValue(baseSummary);

        render(<DataCoveragePanel isExpanded={true} />);
        fireEvent.click(screen.getByRole('button', { name: 'Open data coverage summary' }));

        expect(await screen.findByText('Data Coverage')).toBeInTheDocument();
        expect(screen.queryByText(/Dataset join completeness/)).not.toBeInTheDocument();
    });
});
