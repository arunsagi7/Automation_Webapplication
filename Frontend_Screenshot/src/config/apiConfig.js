// If a backend URL is injected via window.API_BASE_URL (set in index.html),
// use that. Otherwise fall back to same-origin (local dev / FastAPI serving the frontend).
export const API_BASE_URL =
  typeof window !== 'undefined' && window.API_BASE_URL
    ? window.API_BASE_URL.replace(/\/$/, '')
    : (typeof window !== 'undefined' && window.location.protocol !== 'file:'
        ? window.location.origin
        : 'http://127.0.0.1:8001');
