export class ApiError extends Error {
  constructor(message, { status = 0, code = 'request_failed', details = [] } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export async function request(path, { method = 'GET', body, signal } = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers: { Accept: 'application/json', ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      signal,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new ApiError('Unable to reach StockFlow. Check your connection and try again.', { code: 'network_error' });
  }
  if (response.status === 204) return null;
  let data;
  try { data = await response.json(); } catch { data = null; }
  if (!response.ok) {
    const problem = data?.error;
    throw new ApiError(problem?.message || 'StockFlow is temporarily unavailable. Please try again.', {
      status: response.status,
      code: problem?.code || 'service_unavailable',
      details: problem?.details || [],
    });
  }
  if (data === null) throw new ApiError('The server returned an unexpected response. Please try again.', { code: 'invalid_response' });
  return data;
}

export function queryString(params = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== '' && value !== undefined && value !== null) query.set(key, String(value));
  }
  return query.size ? `?${query}` : '';
}

export const api = {
  dashboard: (signal) => request('/dashboard', { signal }),
  categories: (signal) => request('/products/categories', { signal }),
  products: (params, signal) => request(`/products${queryString(params)}`, { signal }),
  product: (id, signal) => request(`/products/${id}`, { signal }),
  createProduct: (body) => request('/products', { method: 'POST', body }),
  updateProduct: (id, body) => request(`/products/${id}`, { method: 'PUT', body }),
  deleteProduct: (id) => request(`/products/${id}`, { method: 'DELETE' }),
  createMovement: (id, body) => request(`/products/${id}/movements`, { method: 'POST', body }),
  movements: (id, params, signal) => request(`/products/${id}/movements${queryString(params)}`, { signal }),
};
