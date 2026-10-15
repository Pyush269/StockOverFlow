import assert from 'node:assert/strict';
import { afterEach, test } from 'node:test';
import { ApiError, queryString, request } from '../src/services/api.js';
import { integerInput, MAX_QUANTITY, money, stockState, validateProduct } from '../src/lib/format.js';

const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });

test('writes use the relative API and JSON contract', async () => {
  let received;
  globalThis.fetch = async (...args) => { received = args; return new Response('{"id":1}', { status: 201 }); };
  assert.equal((await request('/products', { method: 'POST', body: { sku: 'HUB' } })).id, 1);
  assert.equal(received[0], '/api/products');
  assert.equal(received[1].headers['Content-Type'], 'application/json');
  assert.deepEqual(JSON.parse(received[1].body), { sku: 'HUB' });
});

test('an empty successful DELETE does not attempt JSON parsing', async () => {
  globalThis.fetch = async () => new Response(null, { status: 204 });
  assert.equal(await request('/products/1', { method: 'DELETE' }), null);
});

test('business conflicts retain their actionable error code', async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({ error: { code: 'insufficient_stock', message: 'Requested quantity exceeds available stock' } }), { status: 409 });
  await assert.rejects(request('/products/1/movements'), (error) => error instanceof ApiError && error.status === 409 && error.code === 'insufficient_stock');
});

test('server validation preserves field errors used by forms', async () => {
  const details = [{ field: 'body.unit_price', message: 'Invalid price' }];
  globalThis.fetch = async () => new Response(JSON.stringify({ error: { code: 'validation_error', message: 'Request validation failed', details } }), { status: 422 });
  await assert.rejects(request('/products'), (error) => { assert.deepEqual(error.details, details); return true; });
});

test('proxy HTML errors are sanitized instead of rendered', async () => {
  globalThis.fetch = async () => new Response('<html>proxy failed</html>', { status: 502 });
  await assert.rejects(request('/dashboard'), (error) => error.code === 'service_unavailable' && !error.message.includes('<html>'));
});

test('network failure and intentional cancellation remain distinguishable', async () => {
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch'); };
  await assert.rejects(request('/dashboard'), (error) => error.code === 'network_error');
  globalThis.fetch = async () => { throw new DOMException('Cancelled', 'AbortError'); };
  await assert.rejects(request('/dashboard'), (error) => error.name === 'AbortError');
});

test('search parameters escape text and preserve pagination offset zero', () => {
  const query = new URLSearchParams(queryString({ q: 'Hub & cable', category: '', offset: 0 }).slice(1));
  assert.equal(query.get('q'), 'Hub & cable');
  assert.equal(query.get('offset'), '0');
  assert.equal(query.has('category'), false);
});

test('stock status includes the reorder boundary and distinguishes zero stock', () => {
  assert.equal(stockState({ quantity: 0, reorder_level: 5 }).key, 'out');
  assert.equal(stockState({ quantity: 5, reorder_level: 5 }).key, 'low');
  assert.equal(stockState({ quantity: 6, reorder_level: 5 }).key, 'healthy');
});

test('quantity inputs reject decimals, negative values, and overflow', () => {
  for (const value of ['', '-1', '1.2', '1e3', String(MAX_QUANTITY + 1)]) assert.equal(integerInput(value, 1), null);
  assert.equal(integerInput('10', 1), 10);
  assert.equal(integerInput('0', 1), null);
});

test('product validation checks precision and permits normalized SKUs', () => {
  const valid = { sku: ' hub-01 ', name: 'Hub', category: 'Electronics', unit_price: '19.99', reorder_level: '5' };
  assert.deepEqual(validateProduct(valid), {});
  const invalid = validateProduct({ ...valid, unit_price: '19.999', reorder_level: '-1' });
  assert.ok(invalid.unit_price);
  assert.ok(invalid.reorder_level);
});

test('large exact currency strings are not rounded through JavaScript Number', () => {
  assert.equal(money('9007199254740993.25').replace(/[^\d.]/g, ''), '9007199254740993.25');
});
