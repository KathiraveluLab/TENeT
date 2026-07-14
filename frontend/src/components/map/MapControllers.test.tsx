import { useState } from 'react';
import { act, render } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const leaflet = vi.hoisted(() => ({
    events: {} as Record<string, () => void>,
    map: {
        getCenter: vi.fn(),
        getZoom: vi.fn(),
        setView: vi.fn(),
    },
}));

vi.mock('react-leaflet', () => ({
    useMap: () => leaflet.map,
    useMapEvents: (events: Record<string, () => void>) => {
        leaflet.events = events;
        return leaflet.map;
    },
}));

import { MapViewportController } from './MapControllers';

describe('MapViewportController', () => {
    beforeEach(() => {
        leaflet.map.getCenter.mockReturnValue({ lat: 64.2, lng: -152 });
        leaflet.map.getZoom.mockReturnValue(4);
        leaflet.map.setView.mockReset();
    });

    it('keeps a fractional smooth-zoom viewport out of React state', () => {
        const onReport = vi.fn();

        function Harness() {
            const [viewport, setViewport] = useState({
                center: [64.2, -152] as [number, number],
                zoom: 4,
            });

            return (
                <MapViewportController
                    center={viewport.center}
                    zoom={viewport.zoom}
                    onViewportChange={(center, zoom) => {
                        onReport(center, zoom);
                        setViewport({ center, zoom });
                    }}
                />
            );
        }

        render(<Harness />);
        leaflet.map.getCenter.mockReturnValue({ lat: 63.310674, lng: -158.426754 });
        leaflet.map.getZoom.mockReturnValue(4.54046159397577);

        act(() => leaflet.events.moveend());

        expect(onReport).not.toHaveBeenCalled();
        expect(leaflet.map.setView).not.toHaveBeenCalled();
    });
});
