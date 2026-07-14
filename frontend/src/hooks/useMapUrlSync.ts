import { useEffect } from 'react';
import {
    parseMapUrlState,
    serializeMapUrlState,
    type ParsedMapUrlState,
    type SerializableMapUrlState,
} from '../domain/mapUrlState';

export function useMapUrlSync(
    state: SerializableMapUrlState,
    restoreState: (state: ParsedMapUrlState) => void,
): void {
    useEffect(() => {
        if (typeof window === 'undefined') return;
        const search = serializeMapUrlState(window.location.search, state);
        const nextUrl = `${window.location.pathname}${search ? `?${search}` : ''}`;
        window.history.replaceState(null, '', nextUrl);
    }, [state]);

    useEffect(() => {
        if (typeof window === 'undefined') return;
        const handlePopState = () => restoreState(parseMapUrlState(window.location.search));
        window.addEventListener('popstate', handlePopState);
        return () => window.removeEventListener('popstate', handlePopState);
    }, [restoreState]);
}
