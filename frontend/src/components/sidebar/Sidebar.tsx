import {
    useCallback,
    useEffect,
    useMemo,
    useState,
    type KeyboardEvent as ReactKeyboardEvent,
    type MouseEvent as ReactMouseEvent,
} from 'react';
import { RegionSummary } from '../../api/catApi';
import { Season } from '../../api/catApi';
import type { BaseMapLayer } from '../../domain/mapMode';
import type { ScenarioRegion } from '../../types/scenario';
import FilterControls from './FilterControls';
import RegionList from './RegionList';
import SearchBar from './SearchBar';
import SelectedRegionPanel from './SelectedRegionPanel';
import SortControls from './SortControls';
import QuickFilterChips from './QuickFilterChips';
import Button from '../ui/Button';
import {
    filterRegions,
    RegionSortMode,
    SidebarFilters,
    sortRegions,
} from './sidebarUtils';
import './sidebar.css';

interface SidebarProps {
    regions: RegionSummary[];
    loading: boolean;
    error: string | null;
    selectedRegionCode: string | null;
    detailsFocusKey?: number;
    season?: Season;
    activeLayer?: BaseMapLayer;
    pinnedRegionCodes?: string[];
    maxPinnedRegions?: number;
    scenarioRegion?: ScenarioRegion;
    onSelectRegion: (regionCode: string) => void;
    onTogglePin?: (regionCode: string) => void;
    isPinned?: (regionCode: string) => boolean;
    onVisibleRegionsChange?: (regionCodes: string[]) => void;
}

const DEFAULT_FILTERS: SidebarFilters = {
    tier: '',
    status: '',
    desert: '',
    dataGap: 'all',
};

const MIN_SIDEBAR_WIDTH = 300;
const MAX_SIDEBAR_WIDTH = 520;

export default function Sidebar({
    regions,
    loading,
    error,
    selectedRegionCode,
    detailsFocusKey = 0,
    season = 'year_round',
    activeLayer = 'cat',
    pinnedRegionCodes,
    maxPinnedRegions,
    scenarioRegion,
    onSelectRegion,
    onTogglePin,
    isPinned,
    onVisibleRegionsChange,
}: SidebarProps) {
    const [query, setQuery] = useState('');
    const [filters, setFilters] = useState<SidebarFilters>(DEFAULT_FILTERS);
    const [sortMode, setSortMode] = useState<RegionSortMode>('name');
    const [filtersOpen, setFiltersOpen] = useState(false);
    const [isCollapsed, setIsCollapsed] = useState(false);
    const [sidebarWidth, setSidebarWidth] = useState(360);
    const activePinnedRegionCodes = pinnedRegionCodes ?? [];
    const activeMaxPinnedRegions = maxPinnedRegions ?? 3;
    const activeTogglePin = onTogglePin ?? (() => {});
    const activeIsPinned = isPinned ?? (() => false);
    const showCatTools = activeLayer === 'cat';
    const activeFilterCount = [filters.tier, filters.status, filters.desert]
        .filter(Boolean).length + (filters.dataGap === 'all' ? 0 : 1);
    const hasActiveControls = Boolean(query) || activeFilterCount > 0 || sortMode !== 'name';

    const selectedRegion = useMemo(
        () => regions.find(region => region.region_code === selectedRegionCode) ?? null,
        [regions, selectedRegionCode],
    );

    const pinnedRegions = useMemo(
        () => activePinnedRegionCodes
            .map(code => regions.find(region => region.region_code === code))
            .filter((region): region is RegionSummary => Boolean(region)),
        [activePinnedRegionCodes, regions],
    );

    const visibleRegions = useMemo(() => {
        const filtered = filterRegions(regions, query, showCatTools ? filters : DEFAULT_FILTERS);
        return sortRegions(filtered, showCatTools ? sortMode : 'name');
    }, [regions, query, filters, showCatTools, sortMode]);

    useEffect(() => {
        onVisibleRegionsChange?.(visibleRegions.map(region => region.region_code));
    }, [onVisibleRegionsChange, visibleRegions]);

    const resetSidebarControls = useCallback(() => {
        setQuery('');
        setFilters(DEFAULT_FILTERS);
        setSortMode('name');
    }, []);

    const startResize = useCallback((event: ReactMouseEvent<HTMLDivElement>) => {
        event.preventDefault();
        const startX = event.clientX;
        const startWidth = sidebarWidth;

        const handleMove = (moveEvent: MouseEvent) => {
            const nextWidth = Math.min(
                Math.max(startWidth + moveEvent.clientX - startX, MIN_SIDEBAR_WIDTH),
                MAX_SIDEBAR_WIDTH,
            );
            setSidebarWidth(nextWidth);
        };

        const handleUp = () => {
            document.removeEventListener('mousemove', handleMove);
            document.removeEventListener('mouseup', handleUp);
        };

        document.addEventListener('mousemove', handleMove);
        document.addEventListener('mouseup', handleUp);
    }, [sidebarWidth]);

    const resizeWithKeyboard = useCallback((event: ReactKeyboardEvent<HTMLDivElement>) => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();
        if (event.key === 'Home') {
            setSidebarWidth(MIN_SIDEBAR_WIDTH);
            return;
        }
        if (event.key === 'End') {
            setSidebarWidth(MAX_SIDEBAR_WIDTH);
            return;
        }
        const delta = event.key === 'ArrowRight' ? 16 : -16;
        setSidebarWidth(width => Math.min(Math.max(width + delta, MIN_SIDEBAR_WIDTH), MAX_SIDEBAR_WIDTH));
    }, []);

    if (isCollapsed) {
        return (
            <aside
                className="tenet-sidebar collapsed"
                style={{ width: 56, minWidth: 56 }}
                aria-label="Collapsed community sidebar"
            >
                <Button
                    size="small"
                    onClick={() => setIsCollapsed(false)}
                    aria-label="Expand community sidebar"
                >
                    Open
                </Button>
                <div className="sidebar-collapsed-label">Communities</div>
            </aside>
        );
    }

    return (
        <aside
            className="tenet-sidebar"
            style={{ width: sidebarWidth, minWidth: sidebarWidth }}
        >
            <header className="sidebar-header">
                <div>
                    <h1>Communities</h1>
                    <p>{loading ? 'Loading...' : `${visibleRegions.length} of ${regions.length}`}</p>
                </div>
                <div className="sidebar-header-actions">
                    <Button
                        variant="ghost"
                        size="small"
                        onClick={() => setIsCollapsed(true)}
                        aria-label="Collapse community sidebar"
                    >
                        Hide
                    </Button>
                </div>
            </header>

            <SearchBar
                value={query}
                onChange={setQuery}
                onSelectRegion={onSelectRegion}
            />

            {showCatTools && (
                <>
                    <QuickFilterChips filters={filters} onChange={setFilters} />
                    <section className="sidebar-control-panel" aria-label="Community controls">
                        <div className="sidebar-control-panel__header">
                            <button
                                type="button"
                                className="sidebar-control-panel__toggle"
                                aria-expanded={filtersOpen}
                                aria-controls="sidebar-filter-controls"
                                onClick={() => setFiltersOpen(value => !value)}
                            >
                                Filters &amp; sort
                                {activeFilterCount > 0 && (
                                    <span>{activeFilterCount} active</span>
                                )}
                            </button>
                            <Button
                                variant="ghost"
                                size="small"
                                onClick={resetSidebarControls}
                                disabled={!hasActiveControls}
                                aria-label="Reset sidebar filters"
                            >
                                Reset
                            </Button>
                        </div>
                        <div
                            id="sidebar-filter-controls"
                            className="sidebar-control-panel__body"
                            hidden={!filtersOpen}
                        >
                            <FilterControls filters={filters} onChange={setFilters} />
                            <SortControls value={sortMode} onChange={setSortMode} />
                        </div>
                    </section>
                </>
            )}

            {error && <div className="sidebar-error">{error}</div>}

            {showCatTools && pinnedRegions.length > 0 && (
                <section className="pinned-section">
                    <div className="sidebar-section-title">
                        Pinned {pinnedRegions.length}/{activeMaxPinnedRegions}
                    </div>
                    <RegionList
                        regions={pinnedRegions}
                        selectedRegionCode={selectedRegionCode}
                        pinnedRegionCodes={activePinnedRegionCodes}
                        maxPinnedRegions={activeMaxPinnedRegions}
                        showCatDetails={showCatTools}
                        showPin={showCatTools}
                        onSelectRegion={onSelectRegion}
                        onTogglePin={activeTogglePin}
                    />
                </section>
            )}

            <SelectedRegionPanel
                region={selectedRegion}
                season={season}
                focusKey={detailsFocusKey}
                activeLayer={activeLayer}
                pinned={selectedRegion ? activeIsPinned(selectedRegion.region_code) : false}
                pinDisabled={activePinnedRegionCodes.length >= activeMaxPinnedRegions}
                onTogglePin={activeTogglePin}
                scenarioRegion={scenarioRegion}
            />

            <section className="sidebar-results">
                <div className="sidebar-section-title">Results</div>
                {loading ? (
                    <div className="region-list-empty">Loading communities...</div>
                ) : (
                    <RegionList
                        regions={visibleRegions}
                        selectedRegionCode={selectedRegionCode}
                        pinnedRegionCodes={activePinnedRegionCodes}
                        maxPinnedRegions={activeMaxPinnedRegions}
                        showCatDetails={showCatTools}
                        showPin={showCatTools}
                        onSelectRegion={onSelectRegion}
                        onTogglePin={activeTogglePin}
                    />
                )}
            </section>
            <div
                className="sidebar-resize-handle"
                role="separator"
                tabIndex={0}
                aria-orientation="vertical"
                aria-label="Resize community sidebar"
                aria-valuemin={MIN_SIDEBAR_WIDTH}
                aria-valuemax={MAX_SIDEBAR_WIDTH}
                aria-valuenow={sidebarWidth}
                aria-valuetext={`${sidebarWidth} pixels`}
                onMouseDown={startResize}
                onKeyDown={resizeWithKeyboard}
            />
        </aside>
    );
}
