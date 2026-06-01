import React from 'react';
import { getNeedColor, getNeedLabel } from '../api/catApi';
import MetricTooltip from './MetricTooltip';
import './Legend.css';

interface LegendProps {
    totalRegions?: number;
}

const getNeedCapability = (score: number): string => {
    if (score >= 75) return 'Severe lack of nearby healthcare facilities';
    if (score >= 50) return 'Limited access to clinics or hospitals';
    if (score >= 25) return 'Adequate access with some travel distance';
    return 'Good access to nearby healthcare facilities';
};

export default function Legend({ totalRegions }: LegendProps) {
    const needLevels = [87, 62, 37, 12];

    return (
        <div className="legend-hover-shell">
            <button type="button" className="legend-trigger" aria-label="Show discovery legend">
                Legend
            </button>

            <div className="legend-panel">
                <div className="legend-header">
                    <h4>Discovery Legend</h4>
                    <span>Plain-language guide</span>
                </div>

                <div className="legend-section-title">
                    Healthcare Desert Score
                    <MetricTooltip term="Healthcare Desert Score">
                        A 0-100 need score. Higher means the community has farther or weaker access to nearby healthcare.
                    </MetricTooltip>
                </div>

                {needLevels.map(score => (
                    <div key={score} className="legend-row">
                        <span
                            className="legend-dot"
                            style={{ backgroundColor: getNeedColor(score) }}
                            aria-hidden="true"
                        />
                        <div>
                            <div className="legend-row-label">{getNeedLabel(score)}</div>
                            <div className="legend-row-note">{getNeedCapability(score)}</div>
                        </div>
                    </div>
                ))}

                <div className="legend-section">
                    <div className="legend-section-title">
                        CAT Tiers
                        <MetricTooltip term="CAT Tier">
                            Community Access Tier summarizes how isolated a community is for practical care access and transport.
                        </MetricTooltip>
                    </div>
                    <div className="legend-tier-list">
                        <div><strong>Tier 1:</strong> strongest access; road-connected or easier service reach.</div>
                        <div><strong>Tier 2:</strong> moderate access; some travel or logistics constraints.</div>
                        <div><strong>Tier 3:</strong> limited access; remote travel makes care harder to reach.</div>
                        <div><strong>Tier 4:</strong> most isolated; highest transport and service-access barriers.</div>
                    </div>
                </div>

                {totalRegions !== undefined && (
                    <div className="legend-footer-row">
                        <span>Communities</span>
                        <strong>{totalRegions}</strong>
                    </div>
                )}

                <div className="legend-scale">
                    <div
                        className="legend-gradient"
                        style={{
                            background: `linear-gradient(to right, ${getNeedColor(12)}, ${getNeedColor(37)}, ${getNeedColor(62)}, ${getNeedColor(87)})`,
                        }}
                    />
                    <div className="legend-scale-labels">
                        <span>Low Need</span>
                        <span>High Need</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
