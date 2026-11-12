import { describe, expect, it } from 'vitest';
import type { RegionSummary } from '../../api/catApi';
import { BASE_TELEHEALTH_STATUSES } from '../../domain/statusPresentation';
import { filterRegions, type SidebarFilters } from './sidebarUtils';

const emptyFilters: SidebarFilters = {
    tier: '',
    status: '',
    desert: '',
    dataGap: 'all',
};

const regions: RegionSummary[] = [
    {
        id: 1,
        region_code: 'AK-ANC',
        name: 'Anchorage',
        lat: 61.2,
        lon: -149.9,
        cat_tier: 1,
        telehealth_status: 'TELEHEALTH_READY',
        desert_score: 12.5,
        affordability_status: 'affordable',
        data_confidence: 'high',
        has_data_gap: false,
        region: 'Anchorage Municipality',
    },
    {
        id: 2,
        region_code: 'AK-LIM',
        name: 'Cordova',
        lat: 60.5,
        lon: -145.7,
        cat_tier: 3,
        telehealth_status: 'LIMITED_TELEHEALTH',
        desert_score: 52.0,
        affordability_status: 'affordable',
        data_confidence: 'medium',
        has_data_gap: false,
        region: 'Chugach Census Area',
    },
    {
        id: 3,
        region_code: 'AK-ATK',
        name: 'Atka',
        lat: 52.2,
        lon: -174.2,
        cat_tier: 4,
        telehealth_status: 'CRITICAL_GAP',
        desert_score: 78.0,
        affordability_status: 'unaffordable',
        data_confidence: 'low',
        has_data_gap: true,
        region: 'Aleutians West Census Area',
    },
];

describe('sidebarUtils and status presentation parity', () => {
    it('exposes LIMITED_TELEHEALTH as a first-class base status', () => {
        expect(BASE_TELEHEALTH_STATUSES).toContain('LIMITED_TELEHEALTH');
    });

    it('parses tokenized search filters matching backend search semantics', () => {
        expect(filterRegions(regions, 'tier:3', emptyFilters).map(r => r.name)).toEqual(['Cordova']);
        expect(filterRegions(regions, 'status:limited', emptyFilters).map(r => r.name)).toEqual(['Cordova']);
        expect(filterRegions(regions, 'desert:>70', emptyFilters).map(r => r.name)).toEqual(['Atka']);
        expect(filterRegions(regions, 'data:missing', emptyFilters).map(r => r.name)).toEqual(['Atka']);
        expect(filterRegions(regions, 'region:aleutians', emptyFilters).map(r => r.name)).toEqual(['Atka']);
        expect(
            filterRegions(regions, 'tier:4 status:critical desert:>=75', emptyFilters).map(r => r.name),
        ).toEqual(['Atka']);
    });
});

