import { KeyboardEvent, useEffect, useId, useMemo, useRef, useState } from 'react';
import { RegionSummary } from '../../api/catApi';
import { useRegionSearch } from '../../hooks/useRegionSearch';
import { getTelehealthStatusLabel, getTelehealthStatusTone } from '../../domain/statusPresentation';
import StatusBadge from '../ui/StatusBadge';

interface SearchBarProps {
    value: string;
    onChange: (value: string) => void;
    onSelectRegion: (regionCode: string) => void;
}

export default function SearchBar({ value, onChange, onSelectRegion }: SearchBarProps) {
    const [isOpen, setIsOpen] = useState(false);
    const rootRef = useRef<HTMLDivElement>(null);
    const listboxId = useId();
    const searchParams = useMemo(() => ({ q: value }), [value]);
    const { results } = useRegionSearch(searchParams);
    const dropdownResults = value.trim() ? results.slice(0, 8) : [];
    const listboxOpen = isOpen && dropdownResults.length > 0;

    useEffect(() => {
        if (!isOpen) return;
        const handlePointerDown = (event: PointerEvent) => {
            if (!rootRef.current?.contains(event.target as Node)) setIsOpen(false);
        };
        document.addEventListener('pointerdown', handlePointerDown);
        return () => document.removeEventListener('pointerdown', handlePointerDown);
    }, [isOpen]);

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
        <div className="sidebar-search" ref={rootRef}>
            <input
                role="combobox"
                aria-label="Search communities"
                aria-autocomplete="list"
                aria-expanded={listboxOpen}
                aria-controls={listboxId}
                data-testid="community-search"
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
            {listboxOpen && (
                <div className="sidebar-autocomplete" role="listbox" id={listboxId} aria-label="Community suggestions">
                    {dropdownResults.map(region => (
                        <button
                            key={region.region_code}
                            className="sidebar-autocomplete-row"
                            data-testid="sidebar-search-result"
                            role="option"
                            aria-selected="false"
                            onClick={() => selectRegion(region)}
                            type="button"
                        >
                            <span>
                                <strong>{region.name}</strong>
                                <small>CAT {region.cat_tier ?? 'Unknown'}</small>
                            </span>
                            <StatusBadge tone={getTelehealthStatusTone(region.telehealth_status)}>
                                {getTelehealthStatusLabel(region.telehealth_status)}
                            </StatusBadge>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
