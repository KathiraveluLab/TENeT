import { DataGapFilter, SidebarFilters } from './sidebarUtils';

interface FilterControlsProps {
    filters: SidebarFilters;
    onChange: (filters: SidebarFilters) => void;
}

const STATUS_OPTIONS = [
    { value: '', label: 'All statuses' },
    { value: 'TELEHEALTH_READY', label: 'Ready' },
    { value: 'COMMUNITY_ANCHOR', label: 'Anchor' },
    { value: 'CRITICAL_GAP', label: 'Critical' },
    { value: 'DATA_UNAVAILABLE', label: 'Unknown' },
];

export default function FilterControls({ filters, onChange }: FilterControlsProps) {
    return (
        <div className="sidebar-filter-grid">
            <label>
                CAT tier
                <select
                    value={filters.tier}
                    onChange={(event) => onChange({ ...filters, tier: event.target.value })}
                >
                    <option value="">All tiers</option>
                    <option value="1">Tier 1</option>
                    <option value="2">Tier 2</option>
                    <option value="3">Tier 3</option>
                    <option value="4">Tier 4</option>
                </select>
            </label>

            <label>
                Status
                <select
                    value={filters.status}
                    onChange={(event) => onChange({ ...filters, status: event.target.value })}
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
                    onChange={(event) => onChange({ ...filters, desert: event.target.value })}
                >
                    <option value="">All scores</option>
                    <option value="70-plus">70+ severe need</option>
                    <option value="50-plus">50+ high need</option>
                    <option value="below-50">Below 50</option>
                    <option value="unknown">Unknown score</option>
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
