import { describe, expect, it } from 'vitest';
import { escapeHtml } from './escapeHtml';

describe('escapeHtml', () => {
    it('escapes backend text before it is inserted into Leaflet HTML', () => {
        expect(escapeHtml('<img src=x onerror="alert(1)"> & test')).toBe(
            '&lt;img src=x onerror=&quot;alert(1)&quot;&gt; &amp; test',
        );
    });
});
