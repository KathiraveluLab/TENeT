import type { SidebarFilters } from './sidebarUtils';

interface QuickFilterChipsProps {
    filters: SidebarFilters;
    onChange: (filters: SidebarFilters) => void;
}

interface QuickFilter {
    id: string;
    label: string;
    isActive: (filters: SidebarFilters) => boolean;
    toggle: (filters: SidebarFilters) => SidebarFilters;
}

const QUICK_FILTERS: QuickFilter[] = [
    {
        id: 'critical',
        label: 'Critical gaps',
        isActive: filters => filters.status === 'CRITICAL_GAP',
        toggle: filters => ({
            ...filters,
            status: filters.status === 'CRITICAL_GAP' ? '' : 'CRITICAL_GAP',
        }),
    },
    {
        id: 'desert',
        label: 'High desert score',
        isActive: filters => filters.desert === '75-plus',
        toggle: filters => ({
            ...filters,
            desert: filters.desert === '75-plus' ? '' : '75-plus',
        }),
    },
    {
        id: 'incomplete',
        label: 'Data incomplete',
        isActive: filters => filters.dataGap === 'missing',
        toggle: filters => ({
            ...filters,
            dataGap: filters.dataGap === 'missing' ? 'all' : 'missing',
        }),
    },
    {
        id: 'ready',
        label: 'Telehealth ready',
        isActive: filters => filters.status === 'TELEHEALTH_READY',
        toggle: filters => ({
            ...filters,
            status: filters.status === 'TELEHEALTH_READY' ? '' : 'TELEHEALTH_READY',
        }),
    },
];

export default function QuickFilterChips({ filters, onChange }: QuickFilterChipsProps) {
    return (
        <div className="sidebar-quick-filters" aria-label="Quick filters">
            {QUICK_FILTERS.map(filter => {
                const active = filter.isActive(filters);
                return (
                    <button
                        key={filter.id}
                        type="button"
                        className={`sidebar-filter-chip${active ? ' is-active' : ''}`}
                        aria-pressed={active}
                        onClick={() => onChange(filter.toggle(filters))}
                    >
                        {filter.label}
                    </button>
                );
            })}
        </div>
    );
}
