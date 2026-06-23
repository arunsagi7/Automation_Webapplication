// If a backend URL is injected via window.API_BASE_URL (set in index.html / Netlify),
// use that. Otherwise fall back to same-origin (local dev / FastAPI serving the frontend).
export const API_BASE_URL = (() => {
    if (window.API_BASE_URL) return window.API_BASE_URL.replace(/\/$/, '');
    const { protocol, origin } = window.location;
    if (protocol === 'http:' || protocol === 'https:') return origin;
    return 'http://127.0.0.1:8001';
})();
