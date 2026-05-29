import { KeyboardEvent, useMemo, useState } from 'react';
import { RegionSummary } from '../../api/catApi';
import { useRegionSearch } from '../../hooks/useRegionSearch';
import { formatStatus, statusClassName } from './sidebarUtils';

interface SearchBarProps {
    value: string;
    onChange: (value: string) => void;
    onSelectRegion: (regionCode: string) => void;
}

export default function SearchBar({ value, onChange, onSelectRegion }: SearchBarProps) {
    const [isOpen, setIsOpen] = useState(false);
    const searchParams = useMemo(() => ({ q: value }), [value]);
    const { results } = useRegionSearch(searchParams);
    const dropdownResults = value.trim() ? results.slice(0, 8) : [];

    function selectRegion(region: RegionSummary) {
        onSelectRegion(region.region_code);
        setIsOpen(false);
    }

    function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
        if (event.key === 'Enter' && dropdownResults[0]) {
            event.preventDefault();
            selectRegion(dropdownResults[0]);
        }
        if (event.key === 'Escape') {
            setIsOpen(false);
        }
    }

    return (
        <div className="sidebar-search">
            <input
                aria-label="Search communities"
                value={value}
                onChange={(event) => {
                    onChange(event.target.value);
                    setIsOpen(true);
                }}
                onFocus={() => setIsOpen(true)}
                onKeyDown={handleKeyDown}
                placeholder="Search communities"
                className="sidebar-search-input"
            />
            {isOpen && dropdownResults.length > 0 && (
                <div className="sidebar-autocomplete" role="listbox">
                    {dropdownResults.map(region => (
                        <button
                            key={region.region_code}
                            className="sidebar-autocomplete-row"
                            onClick={() => selectRegion(region)}
                            type="button"
                        >
                            <span>
                                <strong>{region.name}</strong>
                                <small>CAT {region.cat_tier ?? 'Unknown'}</small>
                            </span>
                            <span className={`status-badge ${statusClassName(region.telehealth_status)}`}>
                                {formatStatus(region.telehealth_status)}
                            </span>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
