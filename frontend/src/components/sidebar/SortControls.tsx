import { RegionSortMode } from './sidebarUtils';

interface SortControlsProps {
    value: RegionSortMode;
    onChange: (value: RegionSortMode) => void;
}

export default function SortControls({ value, onChange }: SortControlsProps) {
    return (
        <label className="sidebar-sort">
            Sort
            <select
                value={value}
                onChange={(event) => onChange(event.target.value as RegionSortMode)}
            >
                <option value="name">Alphabetical</option>
                <option value="tier">CAT tier</option>
                <option value="desert">Desert score</option>
            </select>
        </label>
    );
}
