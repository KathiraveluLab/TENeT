import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, fetchJson, isAbortError, withQuery } from './http';

afterEach(() => {
    vi.unstubAllGlobals();
});

describe('fetchJson', () => {
    it('returns typed JSON and forwards the abort signal', async () => {
        const controller = new AbortController();
        const fetchMock = vi.fn().mockResolvedValue(new Response(
            JSON.stringify({ count: 3 }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));
        vi.stubGlobal('fetch', fetchMock);

        await expect(fetchJson<{ count: number }>('/api/example', {
            signal: controller.signal,
        })).resolves.toEqual({ count: 3 });
        expect(fetchMock).toHaveBeenCalledWith('/api/example', { signal: controller.signal });
    });

    it('throws an ApiError with response metadata and backend detail', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
            JSON.stringify({ error: 'Not available for this period' }),
            { status: 404, statusText: 'Not Found', headers: { 'Content-Type': 'application/json' } },
        )));

        const request = fetchJson('/api/example', {}, 'Could not load example');
        await expect(request).rejects.toMatchObject({
            name: 'ApiError',
            status: 404,
            statusText: 'Not Found',
            message: 'Could not load example: Not available for this period',
        } satisfies Partial<ApiError>);
    });

    it('normalizes network failures but preserves abort errors', async () => {
        vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new TypeError('offline')));
        await expect(fetchJson('/api/example')).rejects.toMatchObject({
            name: 'ApiError',
            status: 0,
            message: 'This data source is currently unavailable: network request failed',
        });

        const abortError = new DOMException('Cancelled', 'AbortError');
        vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(abortError));
        await expect(fetchJson('/api/example')).rejects.toBe(abortError);
    });
});

describe('HTTP helpers', () => {
    it('builds queries without empty values', () => {
        expect(withQuery('/api/example', {
            season: 'winter',
            limit: 0,
            optional: null,
        })).toBe('/api/example?season=winter&limit=0');
    });

    it('recognizes abort errors without treating ordinary failures as cancellation', () => {
        expect(isAbortError(new DOMException('Cancelled', 'AbortError'))).toBe(true);
        expect(isAbortError(new Error('Network unavailable'))).toBe(false);
    });
});
