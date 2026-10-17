import { BASE_TELEHEALTH_STATUSES, getTelehealthStatusLabel } from '../../domain/statusPresentation';
import { CAT_TIERS, DESERT_SCORE_FILTER_OPTIONS } from '../../domain/metrics';
import { DataGapFilter, SidebarFilters } from './sidebarUtils';

interface FilterControlsProps {
    filters: SidebarFilters;
    onChange: (filters: SidebarFilters) => void;
}

const STATUS_OPTIONS = [
    { value: '', label: 'All statuses' },
    ...BASE_TELEHEALTH_STATUSES.map(value => ({
        value,
        label: getTelehealthStatusLabel(value),
    })),
];

export default function FilterControls({ filters, onChange }: FilterControlsProps) {
    return (
        <div className="sidebar-filter-grid">
            <label>
                CAT tier
                <select
                    value={filters.tier}
                    onChange={(event) => onChange({
                        ...filters,
                        tier: event.target.value as SidebarFilters['tier'],
                    })}
                >
                    <option value="">All tiers</option>
                    {CAT_TIERS.map(tier => <option key={tier} value={tier}>Tier {tier}</option>)}
                </select>
            </label>

            <label>
                Status
                <select
                    value={filters.status}
                    onChange={(event) => onChange({
                        ...filters,
                        status: event.target.value as SidebarFilters['status'],
                    })}
                >
                    {STATUS_OPTIONS.map(option => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                </select>
            </label>

            <label>
                Desert score
                <select
                    value={filters.desert}
                    onChange={(event) => onChange({
                        ...filters,
                        desert: event.target.value as SidebarFilters['desert'],
                    })}
                >
                    {DESERT_SCORE_FILTER_OPTIONS.map(option => (
                        <option key={option.value || 'all'} value={option.value}>{option.label}</option>
                    ))}
                </select>
            </label>

            <label>
                Data gaps
                <select
                    value={filters.dataGap}
                    onChange={(event) => onChange({
                        ...filters,
                        dataGap: event.target.value as DataGapFilter,
                    })}
                >
                    <option value="all">All records</option>
                    <option value="missing">Data incomplete</option>
                    <option value="complete">Complete data</option>
                </select>
            </label>
        </div>
    );
}
