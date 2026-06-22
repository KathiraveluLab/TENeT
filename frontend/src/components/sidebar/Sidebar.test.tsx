import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { RegionSummary } from '../../api/catApi';
import { usePinnedRegions } from '../../hooks/usePinnedRegions';
import Sidebar from './Sidebar';

const regions: RegionSummary[] = [
    {
        id: 1,
        region_code: 'AK-ANCHORAGE',
        name: 'Anchorage',
        lat: 61.2181,
        lon: -149.9003,
        cat_tier: 1,
        telehealth_status: 'TELEHEALTH_READY',
        desert_score: 11.67,
        affordability_status: 'affordable',
        data_confidence: 'high',
        has_data_gap: false,
        region: 'Southcentral',
    },
    {
        id: 2,
        region_code: 'AK-EARECKSON',
        name: 'Eareckson',
        lat: 52.7123,
        lon: 174.114,
        cat_tier: 4,
        telehealth_status: 'CRITICAL_GAP',
        desert_score: 90,
        affordability_status: 'unknown',
        data_confidence: 'missing',
        has_data_gap: true,
        region: 'Aleutians',
    },
    {
        id: 3,
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
    },
    {
        id: 4,
        region_code: 'AK-MISSING',
        name: 'Missing Data',
        lat: null,
        lon: null,
        cat_tier: null,
        telehealth_status: 'DATA_UNAVAILABLE',
        desert_score: null,
        affordability_status: 'unknown',
        data_confidence: 'missing',
        has_data_gap: true,
        region: null,
    },
];

function renderSidebar(onSelectRegion = vi.fn()) {
    function SidebarHarness() {
        const {
            pinnedRegionCodes,
            isPinned,
            togglePinned,
            maxPinnedRegions,
        } = usePinnedRegions();

        return (
            <Sidebar
                regions={regions}
                loading={false}
                error={null}
                selectedRegionCode={null}
                pinnedRegionCodes={pinnedRegionCodes}
                maxPinnedRegions={maxPinnedRegions}
                onSelectRegion={onSelectRegion}
                onTogglePin={togglePinned}
                isPinned={isPinned}
            />
        );
    }

    render(
        <SidebarHarness />,
    );
    return onSelectRegion;
}

function resultCards() {
    return screen.getAllByTestId('sidebar-result').filter(card => (
        card.closest('.pinned-section') === null
    ));
}

function resultCodes() {
    return resultCards().map(card => card.getAttribute('data-region-code'));
}

function cardByCode(regionCode: string) {
    const card = resultCards().find(item => item.getAttribute('data-region-code') === regionCode);
    if (!card) {
        throw new Error(`Missing region card: ${regionCode}`);
    }
    return card;
}

describe('Sidebar discovery', () => {
    beforeEach(() => {
        window.localStorage.clear();
        vi.stubGlobal('fetch', vi.fn(async () => ({
            ok: true,
            json: async () => ({ regions: [regions[0]], count: 1 }),
            statusText: 'OK',
        })));
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('renders summary regions with safe missing-data labels', () => {
        renderSidebar();

        expect(screen.getByText('Anchorage')).toBeInTheDocument();
        expect(screen.getByText('Eareckson')).toBeInTheDocument();
        expect(screen.getByText('Missing Data')).toBeInTheDocument();
        expect(screen.getAllByText('Data incomplete').length).toBeGreaterThan(0);
        expect(screen.getAllByText('Confidence Missing').length).toBeGreaterThan(0);
        expect(screen.getByText('Desert Unknown')).toBeInTheDocument();
    });

    it('filters by CAT tier', async () => {
        renderSidebar();

        fireEvent.change(screen.getByLabelText(/CAT tier/i), { target: { value: '4' } });

        expect(screen.getByText('Eareckson')).toBeInTheDocument();
        expect(screen.queryByText('Anchorage')).not.toBeInTheDocument();
    });

    it('filters by telehealth status', async () => {
        renderSidebar();

        fireEvent.change(screen.getByLabelText(/Status/i), { target: { value: 'COMMUNITY_ANCHOR' } });

        expect(screen.getByText('Bethel')).toBeInTheDocument();
        expect(screen.queryByText('Eareckson')).not.toBeInTheDocument();
    });

    it('filters by data gaps', async () => {
        renderSidebar();

        fireEvent.change(screen.getByLabelText(/Data gaps/i), { target: { value: 'missing' } });

        expect(screen.getByText('Eareckson')).toBeInTheDocument();
        expect(screen.getByText('Bethel')).toBeInTheDocument();
        expect(screen.queryByText('Anchorage')).not.toBeInTheDocument();
    });

    it('filters by healthcare desert score', async () => {
        renderSidebar();

        fireEvent.change(screen.getByLabelText(/Desert score/i), { target: { value: '70-plus' } });

        expect(screen.getByText('Eareckson')).toBeInTheDocument();
        expect(screen.queryByText('Bethel')).not.toBeInTheDocument();
    });

    it('sorts by name, CAT tier, and desert score', async () => {
        renderSidebar();

        expect(resultCodes()[0]).toBe('AK-ANCHORAGE');

        fireEvent.change(screen.getByLabelText(/Sort/i), { target: { value: 'tier' } });
        expect(resultCodes()[0]).toBe('AK-ANCHORAGE');
        expect(resultCodes()[3]).toBe('AK-MISSING');

        fireEvent.change(screen.getByLabelText(/Sort/i), { target: { value: 'desert' } });
        expect(resultCodes()[0]).toBe('AK-EARECKSON');
        expect(resultCodes()[3]).toBe('AK-MISSING');
    });

    it('resets search, filters, and sort controls', async () => {
        renderSidebar();

        fireEvent.change(screen.getByLabelText(/Search communities/i), { target: { value: 'Bethel' } });
        fireEvent.change(screen.getByLabelText(/CAT tier/i), { target: { value: '3' } });
        fireEvent.change(screen.getByLabelText(/Sort/i), { target: { value: 'desert' } });

        expect(resultCodes()).toEqual(['AK-BETHEL']);

        fireEvent.click(screen.getByRole('button', { name: /Reset sidebar filters/i }));

        expect(screen.getByLabelText(/Search communities/i)).toHaveValue('');
        expect(screen.getByLabelText(/CAT tier/i)).toHaveValue('');
        expect(screen.getByLabelText(/Sort/i)).toHaveValue('name');
        expect(resultCodes()).toEqual([
            'AK-ANCHORAGE',
            'AK-BETHEL',
            'AK-EARECKSON',
            'AK-MISSING',
        ]);
    });

    it('selects a community from the list', async () => {
        const onSelectRegion = renderSidebar();

        fireEvent.click(within(cardByCode('AK-BETHEL')).getAllByRole('button')[0]);

        expect(onSelectRegion).toHaveBeenCalledWith('AK-BETHEL');
    });

    it('shows autocomplete results and Enter selects the top result', async () => {
        const onSelectRegion = renderSidebar();

        fireEvent.change(screen.getByLabelText(/Search communities/i), { target: { value: 'Anch' } });

        const listbox = await screen.findByRole('listbox');
        expect(within(listbox).getByText('Anchorage')).toBeInTheDocument();

        fireEvent.keyDown(screen.getByLabelText(/Search communities/i), { key: 'Enter' });

        await waitFor(() => {
            expect(onSelectRegion).toHaveBeenCalledWith('AK-ANCHORAGE');
        });
    });

    it('Escape closes autocomplete dropdown', async () => {
        renderSidebar();

        fireEvent.change(screen.getByLabelText(/Search communities/i), { target: { value: 'Anch' } });
        expect(await screen.findByRole('listbox')).toBeInTheDocument();

        fireEvent.keyDown(screen.getByLabelText(/Search communities/i), { key: 'Escape' });

        await waitFor(() => {
            expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
        });
    });

    it('pinning persists to localStorage and caps at three communities', async () => {
        renderSidebar();

        fireEvent.click(screen.getByLabelText('Pin Anchorage'));
        fireEvent.click(screen.getByLabelText('Pin Eareckson'));
        fireEvent.click(screen.getByLabelText('Pin Bethel'));

        await waitFor(() => {
            expect(JSON.parse(window.localStorage.getItem('tenet:pinned-regions') || '[]')).toEqual([
                'AK-ANCHORAGE',
                'AK-EARECKSON',
                'AK-BETHEL',
            ]);
        });
        expect(screen.getByLabelText('Pin Missing Data')).toBeDisabled();
    });
});
