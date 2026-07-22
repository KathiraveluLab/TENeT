import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { PerformanceCanvasLayer } from './PerformanceCanvasLayer';

// Mock the custom hook to bypass DOM canvas injection issues in JSDOM
vi.mock('./../hooks/useCanvasOverlay', () => ({
    useCanvasOverlay: vi.fn(),
}));

vi.mock('react-leaflet', () => ({
    useMap: vi.fn().mockReturnValue({
        on: vi.fn(),
        off: vi.fn(),
        getContainer: vi.fn().mockReturnValue({ style: { cursor: '' } }),
        closePopup: vi.fn(),
        project: vi.fn().mockReturnValue({ x: 100, y: 100 }),
        unproject: vi.fn().mockReturnValue({ lat: 60, lng: -150 }),
        mouseEventToContainerPoint: vi.fn().mockReturnValue({ x: 100, y: 100 }),
        containerPointToLayerPoint: vi.fn().mockReturnValue({ x: 100, y: 100 }),
    }),
}));

describe('PerformanceCanvasLayer', () => {
    it('renders without crashing when given valid props', () => {
        const { container } = render(
            <PerformanceCanvasLayer
                visibleTiles={[]}
                affordabilityData={[]}
                useStarlink={false}
                filterMode="combined"
                zoomLevel={5}
            />
        );
        // The custom hook injects a canvas into the map's overlay pane (mocked above),
        // but the component itself renders null in the React tree.
        expect(container.firstChild).toBeNull();
    });
});
