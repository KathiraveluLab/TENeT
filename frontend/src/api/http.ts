export type QueryValue = string | number | boolean | null | undefined;

export class ApiError extends Error {
    readonly status: number;
    readonly statusText: string;
    readonly url: string;
    readonly body: unknown;

    constructor({
        message,
        status,
        statusText,
        url,
        body,
        cause,
    }: {
        message: string;
        status: number;
        statusText: string;
        url: string;
        body?: unknown;
        cause?: unknown;
    }) {
        super(message);
        if (cause !== undefined) {
            (this as Error & { cause?: unknown }).cause = cause;
        }
        this.name = 'ApiError';
        this.status = status;
        this.statusText = statusText;
        this.url = url;
        this.body = body;
    }
}

function responseErrorDetail(body: unknown): string | null {
    if (!body || typeof body !== 'object') return null;
    const candidate = body as { error?: unknown; message?: unknown };
    if (typeof candidate.error === 'string' && candidate.error.trim()) return candidate.error;
    if (typeof candidate.message === 'string' && candidate.message.trim()) return candidate.message;
    return null;
}

async function readErrorBody(response: Response): Promise<unknown> {
    const contentType = response.headers.get('content-type') ?? '';
    try {
        return contentType.includes('application/json')
            ? await response.json()
            : await response.text();
    } catch {
        return null;
    }
}

export async function fetchJson<T>(
    url: string,
    init: RequestInit = {},
    errorMessage = 'This data source is currently unavailable',
): Promise<T> {
    let response: Response;
    try {
        response = await fetch(url, init);
    } catch (cause: unknown) {
        if (isAbortError(cause)) throw cause;
        throw new ApiError({
            message: `${errorMessage}: network request failed`,
            status: 0,
            statusText: '',
            url,
            cause,
        });
    }

    if (!response.ok) {
        const body = await readErrorBody(response);
        const detail = responseErrorDetail(body) || response.statusText;
        throw new ApiError({
            message: detail ? `${errorMessage}: ${detail}` : errorMessage,
            status: response.status,
            statusText: response.statusText,
            url: response.url || url,
            body,
        });
    }

    try {
        return await response.json() as T;
    } catch (cause: unknown) {
        throw new ApiError({
            message: `${errorMessage}: invalid JSON response`,
            status: response.status,
            statusText: response.statusText,
            url: response.url || url,
            cause,
        });
    }
}

export function withQuery<T extends object>(url: string, params: T): string {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]: [string, QueryValue]) => {
        if (value !== undefined && value !== null && value !== '') {
            query.set(key, String(value));
        }
    });
    const suffix = query.toString();
    return suffix ? `${url}?${suffix}` : url;
}

export function isAbortError(error: unknown): boolean {
    return error instanceof DOMException
        ? error.name === 'AbortError'
        : error instanceof Error && error.name === 'AbortError';
}

export function errorMessage(error: unknown, fallback = 'This data source is currently unavailable.'): string {
    if (error instanceof Error && error.message.trim()) return error.message;
    return fallback;
}
