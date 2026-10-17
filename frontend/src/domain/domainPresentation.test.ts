import { describe, expect, it } from 'vitest';
import {
    DESERT_SCORE_THRESHOLDS,
    getDataGapPresentation,
    getDesertScorePresentation,
    matchesDesertScoreFilter,
} from './metrics';
import {
    getTelehealthStatusColor,
    getTelehealthStatusLabel,
    getTelehealthStatusTone,
} from './statusPresentation';

describe('desert score presentation', () => {
    it.each([
        [0, 'adequate', 'Adequate Need'],
        [DESERT_SCORE_THRESHOLDS.moderate - 0.1, 'adequate', 'Adequate Need'],
        [DESERT_SCORE_THRESHOLDS.moderate, 'moderate', 'Moderate Need'],
        [DESERT_SCORE_THRESHOLDS.high, 'high', 'High Need'],
        [DESERT_SCORE_THRESHOLDS.critical, 'critical', 'Critical Need'],
        [100, 'critical', 'Critical Need'],
    ])('classifies %s as %s', (score, level, label) => {
        expect(getDesertScorePresentation(score)).toMatchObject({ level, label });
    });

    it('uses the same thresholds for sidebar score filters', () => {
        expect(matchesDesertScoreFilter(75, '75-plus')).toBe(true);
        expect(matchesDesertScoreFilter(74.9, '75-plus')).toBe(false);
        expect(matchesDesertScoreFilter(50, '50-plus')).toBe(true);
        expect(matchesDesertScoreFilter(49.9, 'below-50')).toBe(true);
        expect(matchesDesertScoreFilter(null, 'unknown')).toBe(true);
    });
});

describe('status presentation', () => {
    it('provides one label, color, and tone for each shared status', () => {
        expect(getTelehealthStatusLabel('COMMUNITY_ANCHOR')).toBe('Community Anchor');
        expect(getTelehealthStatusColor('CRITICAL_GAP')).toBe('#ef4444');
        expect(getTelehealthStatusColor('COMMUNITY_ANCHOR', 'scenario')).toBe('#f97316');
        expect(getTelehealthStatusTone('LIMITED_TELEHEALTH')).toBe('limited');
    });

    it('names satellite dependency as connectivity, not affordability', () => {
        expect(getDataGapPresentation('SATELLITE_DEPENDENT').label).toBe('Satellite-dependent access');
    });
});
