import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchRegionSummary } from './catApi';


afterEach(() => {
    vi.unstubAllGlobals();
});


describe('community summary API', () => {
    it('requests metrics for the selected season', async () => {
        const fetchMock = vi.fn().mockResolvedValue(new Response(
            JSON.stringify({ regions: [], count: 0, season: 'winter' }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));
        vi.stubGlobal('fetch', fetchMock);

        await expect(fetchRegionSummary('winter')).resolves.toEqual([]);
        expect(fetchMock).toHaveBeenCalledWith(
            '/api/cat/regions/summary?season=winter',
            { signal: undefined },
        );
    });
});
