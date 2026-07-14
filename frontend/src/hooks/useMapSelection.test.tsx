import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { useMapSelection } from './useMapSelection';

describe('useMapSelection', () => {
    it('requests selected-panel visibility for selections and detail actions', () => {
        const { result } = renderHook(() => useMapSelection(null));

        act(() => result.current.selectRegion('AK-ANCHORAGE'));
        expect(result.current.selectedRegionCode).toBe('AK-ANCHORAGE');
        expect(result.current.detailsFocusKey).toBe(1);

        act(() => result.current.viewRegionDetails('AK-BETHEL'));
        expect(result.current.selectedRegionCode).toBe('AK-BETHEL');
        expect(result.current.detailsFocusKey).toBe(2);
    });
});
