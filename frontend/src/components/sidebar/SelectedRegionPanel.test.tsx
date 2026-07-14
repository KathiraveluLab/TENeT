import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { RegionSummary } from '../../api/catApi';
import SelectedRegionPanel from './SelectedRegionPanel';

vi.mock('../../hooks/useResearchProfile', () => ({
    useResearchProfile: () => ({
        profile: null,
        loading: false,
        error: null,
    }),
}));

const region: RegionSummary = {
    id: 1,
    region_code: 'AK-BETHEL',
    name: 'Bethel',
    lat: 60.7922,
    lon: -161.7558,
    cat_tier: 3,
    telehealth_status: 'COMMUNITY_ANCHOR',
    desert_score: 55,
    affordability_status: 'unaffordable',
    data_confidence: 'medium',
    has_data_gap: true,
    region: 'Yukon-Kuskokwim',
};

function renderPanel(activeLayer: 'cat' | 'affordability') {
    render(
        <SelectedRegionPanel
            region={region}
            season="year_round"
            activeLayer={activeLayer}
            pinned={false}
            pinDisabled={false}
            onTogglePin={vi.fn()}
        />,
    );
}

describe('SelectedRegionPanel layer details', () => {
    it('shows CAT-first details on the CAT layer', () => {
        renderPanel('cat');

        expect(screen.getByRole('heading', { name: 'CAT access' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Transport evidence' })).toBeInTheDocument();
        expect(screen.getByText(/CAT details/)).toBeInTheDocument();
        expect(screen.getByTestId('cat-region-summary')).toBeInTheDocument();
        expect(screen.queryByTestId('affordability-region-summary')).not.toBeInTheDocument();
        expect(screen.queryByRole('heading', { name: 'Affordability' })).not.toBeInTheDocument();
        expect(screen.queryByText('Cost burden')).not.toBeInTheDocument();
    });

    it('shows affordability details on the affordability layer', () => {
        renderPanel('affordability');

        expect(screen.getByRole('heading', { name: 'Access' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Connectivity' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Affordability' })).toBeInTheDocument();
        expect(screen.getAllByText('Cost burden')).toHaveLength(2);
        expect(screen.getByText(/Affordability details/)).toBeInTheDocument();
        expect(screen.getByTestId('affordability-region-summary')).toBeInTheDocument();
        expect(screen.queryByTestId('cat-region-summary')).not.toBeInTheDocument();
        expect(screen.queryByRole('heading', { name: 'CAT access' })).not.toBeInTheDocument();
    });
});
