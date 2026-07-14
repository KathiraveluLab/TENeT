const HTML_ENTITIES: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
};

export function escapeHtml(value: string | number): string {
    return String(value).replace(/[&<>"']/g, character => HTML_ENTITIES[character]);
}
