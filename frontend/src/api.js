// Thin fetch wrappers around the Expense Tracker API.
//
// All paths are relative (/api/...) on purpose: in development Vite proxies them
// to FastAPI on :8000, in the container nginx proxies them to the backend
// service. The React code therefore never hard-codes a backend hostname.

const BASE = '/api/expenses';

export class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    // FastAPI validation errors arrive as a list of {loc, msg}. Keeping them lets
    // the form highlight the exact field the server rejected.
    this.details = details;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      ...options,
    });
  } catch (err) {
    // Network-level failure (backend down, DNS, nginx 502 before any body...).
    throw new ApiError('Could not reach the Expense Tracker API', 0, null);
  }

  if (response.status === 204) return null;

  let body = null;
  const text = await response.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }

  if (!response.ok) {
    const detail = body && body.detail;
    const message = typeof detail === 'string' ? detail : `Request failed (${response.status})`;
    throw new ApiError(message, response.status, Array.isArray(detail) ? detail : null);
  }
  return body;
}

function buildQuery(filters) {
  const params = new URLSearchParams();
  if (filters.category) params.set('category', filters.category);
  if (filters.month) params.set('month', filters.month);
  if (filters.q && filters.q.trim()) params.set('q', filters.q.trim());
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

export function listExpenses(filters = {}) {
  return request(`${BASE}${buildQuery(filters)}`);
}

export function getSummary() {
  return request(`${BASE}/summary`);
}

export function createExpense(payload) {
  return request(BASE, { method: 'POST', body: JSON.stringify(payload) });
}

export function updateExpense(id, payload) {
  return request(`${BASE}/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
}

export function deleteExpense(id) {
  return request(`${BASE}/${id}`, { method: 'DELETE' });
}
