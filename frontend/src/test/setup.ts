import '@testing-library/jest-dom/vitest';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const localStorageStore: Record<string, string> = {};

Object.defineProperty(window, 'localStorage', {
    value: {
        getItem: (key: string) => localStorageStore[key] ?? null,
        setItem: (key: string, value: string) => {
            localStorageStore[key] = value;
        },
        removeItem: (key: string) => {
            delete localStorageStore[key];
        },
        clear: () => {
            Object.keys(localStorageStore).forEach(key => delete localStorageStore[key]);
        },
        key: (index: number) => Object.keys(localStorageStore)[index] ?? null,
        get length() {
            return Object.keys(localStorageStore).length;
        },
    },
    configurable: true,
});
