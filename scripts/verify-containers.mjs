// Invoked only by test-containers.ps1 against its isolated Compose project.
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';

const mode = process.argv[2];
const origin = 'http://127.0.0.1:3001';
const statePath = new URL('../.logs/container-qa-state.json', import.meta.url);
async function api(path, { method = 'GET', data, status = 200 } = {}) {
  const response = await fetch(`${origin}${path}`, {
    method,
    ...(data ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) } : {}),
    signal: AbortSignal.timeout(10000),
  });
  assert.equal(response.status, status, `${method} ${path}`);
  return response.status === 204 ? null : response.json();
}
const productPath = (id) => `/api/products/${id}`;

if (mode === 'before') {
  const payload = { sku: `CONTAINER-${Date.now()}`, name: 'Container persistence fixture', category: 'Container QA', unit_price: '19.99', reorder_level: 5 };
  const created = await api('/api/products', { method: 'POST', data: payload, status: 201 });
  assert.equal(created.quantity, 0);
  const path = productPath(created.id);
  const updated = await api(path, { method: 'PUT', data: { ...payload, description: 'Must survive Compose down/up' } });
  assert.equal(updated.description, 'Must survive Compose down/up');
  await api('/api/products', { method: 'POST', data: payload, status: 409 });
  await api(path + '/movements', { method: 'POST', data: { movement_type: 'IN', quantity: 10 }, status: 201 });
  const issued = await api(path + '/movements', { method: 'POST', data: { movement_type: 'OUT', quantity: 3 }, status: 201 });
  assert.equal(issued.product.quantity, 7);
  const rejected = await api(path + '/movements', { method: 'POST', data: { movement_type: 'OUT', quantity: 8 }, status: 409 });
  assert.equal(rejected.error.code, 'insufficient_stock');
  await api(path + '/movements', { method: 'POST', data: { movement_type: 'IN', quantity: 0 }, status: 422 });
  await api(path, { method: 'DELETE', status: 409 });
  const product = await api(path);
  const history = await api(path + '/movements');
  assert.equal(product.quantity, 7);
  assert.equal(history.total, 2);
  const unused = await api('/api/products', { method: 'POST', data: { ...payload, sku: payload.sku + '-DELETE' }, status: 201 });
  await api(productPath(unused.id), { method: 'DELETE', status: 204 });
  await api(productPath(unused.id), { status: 404 });
  const listing = await api(`/api/products?q=${encodeURIComponent(payload.sku)}`);
  assert.equal(listing.items[0].id, product.id);
  await writeFile(statePath, JSON.stringify({ product, history }, null, 2));
  console.log('PASS: Nginx-proxied CRUD, SKU conflict, stock 10 - 3 = 7, reject 8, validation, atomic history, and protected deletion.');
} else if (mode === 'after') {
  const expected = JSON.parse(await readFile(statePath, 'utf8'));
  const path = productPath(expected.product.id);
  assert.deepEqual(await api(path), expected.product);
  assert.deepEqual(await api(path + '/movements'), expected.history);
  console.log('PASS: exact product fields, quantity 7, and both ledger entries survived Compose down/up.');
} else {
  throw new Error('Expected before or after verification mode');
}

for (const path of ['/', '/products/deep-link']) {
  const response = await fetch(origin + path);
  assert.equal(response.status, 200);
  assert.match(response.headers.get('content-type'), /text\/html/);
  assert.match(await response.text(), /<div id="root">/);
}
const missingAsset = await fetch(origin + '/assets/does-not-exist.js');
assert.equal(missingAsset.status, 404);
const missingApi = await api('/api/does-not-exist', { status: 404 });
assert.equal(missingApi.error.code, 'http_error');
console.log('PASS: SPA fallback, real missing-asset 404, and JSON API errors preserved through Nginx.');
