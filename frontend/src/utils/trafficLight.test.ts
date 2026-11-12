import { describe, expect, it } from 'vitest';
import { getScenarioCost, getTrafficLightStatus } from './trafficLight';

describe('trafficLight utilities', () => {
    it('uses regional ISP cost when non-Starlink and falls back by latitude', () => {
        expect(getScenarioCost(64.8, true, 450)).toBe(120);
        expect(getScenarioCost(64.8, false, 125)).toBe(125);
        expect(getScenarioCost(60.5, false, 450)).toBe(450);
        expect(getScenarioCost(64.8, false, null)).toBe(450);
        expect(getScenarioCost(61.2, false, undefined)).toBe(125);
    });

    it('applies the rural high-cost threshold strictly above $400', () => {
        expect(getTrafficLightStatus(60, 30, 1.5, 400)).toBe('GREEN');
        expect(getTrafficLightStatus(60, 30, 1.5, 400.01)).toBe('ORANGE');
        expect(getTrafficLightStatus(60, 30, 1.5, 450)).toBe('ORANGE');
    });
});

