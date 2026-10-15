import { test, expect } from '@playwright/test';

const unique = (prefix = 'QA') => `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 7)}`.toUpperCase();
const evidencePrefix = process.env.STOCKFLOW_EVIDENCE_PREFIX || 'frontend';
const rowFor = (page, sku) => page.locator('tbody tr').filter({ hasText: sku });

async function createProduct(request, changes = {}) {
  const payload = { sku: unique(), name: 'Test inventory product', category: 'QA Accessories', unit_price: '19.99', reorder_level: 5, ...changes };
  const response = await request.post('/api/products', { data: payload });
  expect(response.status()).toBe(201);
  return response.json();
}

async function findProduct(page, sku) {
  await page.goto('/#/products');
  await page.getByRole('textbox', { name: 'Search products', exact: true }).fill(sku);
  await expect(rowFor(page, sku)).toHaveCount(1);
}

async function fillProduct(dialog, product) {
  await dialog.getByLabel('Product name', { exact: true }).fill(product.name);
  await dialog.getByLabel('SKU', { exact: true }).fill(product.sku);
  await dialog.getByLabel('Category', { exact: true }).fill(product.category);
  await dialog.getByLabel('Unit price (₹)', { exact: true }).fill(product.unit_price);
  await dialog.getByLabel('Reorder level', { exact: true }).fill('5');
}

test('create, edit, receive, issue, prevent overselling, and inspect the ledger', async ({ page, request }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  const product = { sku: unique('WORKFLOW'), name: 'USB-C Hub · browser check', category: 'Electronics', unit_price: '19.99' };
  await page.goto('/#/products');
  await page.getByRole('button', { name: 'Add product', exact: true }).click();
  const create = page.getByRole('dialog', { name: 'Add a product', exact: true });
  await fillProduct(create, product);
  await create.getByRole('button', { name: 'Add product', exact: true }).click();
  await expect(create).not.toBeVisible();
  await page.getByRole('textbox', { name: 'Search products', exact: true }).fill(product.sku);
  await expect(rowFor(page, product.sku)).toHaveCount(1);

  await page.getByRole('button', { name: `Edit ${product.name}`, exact: true }).click();
  const edit = page.getByRole('dialog', { name: 'Edit product', exact: true });
  product.name = 'USB-C Hub · updated';
  await edit.getByLabel('Product name', { exact: true }).fill(product.name);
  await edit.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(edit).not.toBeVisible();
  await expect(rowFor(page, product.sku)).toContainText(product.name);

  await page.getByRole('button', { name: `Receive stock for ${product.name}`, exact: true }).click();
  let movement = page.getByRole('dialog', { name: 'Record stock movement', exact: true });
  await movement.getByLabel('Quantity', { exact: true }).fill('10');
  await movement.getByLabel('Note (optional)', { exact: true }).fill('Opening browser QA stock');
  await movement.getByRole('button', { name: 'Confirm receipt', exact: true }).click();
  await expect(movement).not.toBeVisible();
  await expect(rowFor(page, product.sku).locator('.quantity-value')).toHaveText('10');

  await page.getByRole('button', { name: `Issue stock for ${product.name}`, exact: true }).click();
  movement = page.getByRole('dialog', { name: 'Record stock movement', exact: true });
  await movement.getByLabel('Quantity', { exact: true }).fill('3');
  await movement.getByLabel('Note (optional)', { exact: true }).fill('Browser QA order');
  await movement.getByRole('button', { name: 'Confirm issue', exact: true }).click();
  await expect(movement).not.toBeVisible();
  await expect(rowFor(page, product.sku).locator('.quantity-value')).toHaveText('7');

  await page.getByRole('button', { name: `Issue stock for ${product.name}`, exact: true }).click();
  await movement.getByLabel('Quantity', { exact: true }).fill('8');
  await expect(movement.getByRole('alert')).toContainText('Only 7 units are available');
  await expect(movement.getByRole('button', { name: 'Confirm issue', exact: true })).toBeDisabled();
  await movement.getByRole('button', { name: 'Cancel', exact: true }).click();

  await page.getByRole('button', { name: `View history for ${product.name}`, exact: true }).click();
  const history = page.getByRole('dialog', { name: 'Stock history', exact: true });
  await expect(history.getByText('Opening browser QA stock', { exact: true })).toBeVisible();
  await expect(history.getByText('Browser QA order', { exact: true })).toBeVisible();
  await expect(history.locator('tbody tr')).toHaveCount(2);
  await history.getByRole('button', { name: 'Done', exact: true }).click();

  await page.getByRole('link', { name: 'Overview', exact: true }).click();
  const expected = await (await request.get('/api/dashboard')).json();
  await expect(page.locator('.stat-card').filter({ hasText: 'Total products' }).locator('.stat-value')).toHaveText(String(expected.total_products));
  await page.screenshot({ path: `../docs/screenshots/${evidencePrefix}-overview-qa.png`, fullPage: true });
  expect(errors).toEqual([]);
});

test('duplicate SKU and temporary save failure preserve form values', async ({ page, request }) => {
  const product = await createProduct(request, { name: 'Duplicate SKU fixture' });
  await page.goto('/#/products');
  await page.getByRole('button', { name: 'Add product', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Add a product', exact: true });
  const payload = { ...product, name: 'Keep these form values' };
  await fillProduct(dialog, payload);
  await dialog.getByRole('button', { name: 'Add product', exact: true }).click();
  await expect(dialog.getByText('This SKU is already in your catalog. Choose a unique SKU.')).toBeVisible();
  await expect(dialog.getByLabel('Product name', { exact: true })).toHaveValue(payload.name);
  await dialog.getByLabel('SKU', { exact: true }).fill(unique('RETRY'));
  const fail = async (route) => {
    if (route.request().method() === 'POST') await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: { code: 'database_unavailable', message: 'Database temporarily unavailable' } }) });
    else await route.continue();
  };
  await page.route('**/api/products', fail);
  await dialog.getByRole('button', { name: 'Add product', exact: true }).click();
  await expect(dialog.getByText('Database temporarily unavailable', { exact: true })).toBeVisible();
  await expect(dialog.getByLabel('Product name', { exact: true })).toHaveValue(payload.name);
  await page.unroute('**/api/products', fail);
  await dialog.getByRole('button', { name: 'Add product', exact: true }).click();
  await expect(dialog).not.toBeVisible();
});

test('delete confirmation can cancel, deletes unused fixtures, and protects ledger history', async ({ page, request }) => {
  const unused = await createProduct(request, { name: 'Unused deletion fixture' });
  await findProduct(page, unused.sku);
  await page.getByRole('button', { name: `Delete ${unused.name}`, exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Delete this product?', exact: true });
  await dialog.getByRole('button', { name: 'Keep product', exact: true }).click();
  await expect(rowFor(page, unused.sku)).toHaveCount(1);
  await page.getByRole('button', { name: `Delete ${unused.name}`, exact: true }).click();
  await dialog.getByRole('button', { name: 'Delete product', exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(rowFor(page, unused.sku)).toHaveCount(0);
  expect((await request.get(`/api/products/${unused.id}`)).status()).toBe(404);

  const protectedProduct = await createProduct(request, { name: 'Ledger-protected fixture' });
  await request.post(`/api/products/${protectedProduct.id}/movements`, { data: { movement_type: 'IN', quantity: 1 } });
  await findProduct(page, protectedProduct.sku);
  await page.getByRole('button', { name: `Delete ${protectedProduct.name}`, exact: true }).click();
  await dialog.getByRole('button', { name: 'Delete product', exact: true }).click();
  await expect(dialog.getByText('Products with movement history cannot be deleted', { exact: true })).toBeVisible();
});

test('category, status, search and pagination work across catalog pages', async ({ page, request }) => {
  const category = unique('PAGING');
  for (let index = 0; index < 12; index++) await createProduct(request, { name: `Pagination fixture ${index}`, category });
  await page.goto('/#/products');
  await expect(page.getByRole('combobox', { name: 'Filter by category' }).locator('option').filter({ hasText: category })).toHaveCount(1);
  await page.getByRole('combobox', { name: 'Filter by category' }).selectOption(category);
  await expect(page.locator('.catalog-panel tbody tr')).toHaveCount(10);
  await page.getByRole('button', { name: 'Next products page' }).click();
  await expect(page.locator('.catalog-panel tbody tr')).toHaveCount(2);
  await page.getByRole('combobox', { name: 'Filter by stock status' }).selectOption('healthy');
  await expect(page.getByText('No products match your filters', { exact: true })).toBeVisible();
  await page.getByRole('combobox', { name: 'Filter by stock status' }).selectOption('out');
  await expect(page.locator('.catalog-panel tbody tr')).toHaveCount(10);
  await page.getByRole('textbox', { name: 'Search products', exact: true }).fill('no-such-product-uniquely');
  await expect(page.getByText('No products match your filters', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Clear filters', exact: true }).first().click();
  await expect(page.locator('.catalog-panel tbody tr')).toHaveCount(10);
});

test('stale stock conflicts retain the quantity and note and refresh availability', async ({ page, request }) => {
  const product = await createProduct(request, { name: 'Concurrent operator fixture' });
  await request.post(`/api/products/${product.id}/movements`, { data: { movement_type: 'IN', quantity: 10 } });
  await findProduct(page, product.sku);
  await page.getByRole('button', { name: `Issue stock for ${product.name}`, exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Record stock movement', exact: true });
  await dialog.getByLabel('Quantity', { exact: true }).fill('8');
  await dialog.getByLabel('Note (optional)', { exact: true }).fill('Keep my note');
  await expect(dialog.getByRole('button', { name: 'Confirm issue', exact: true })).toBeEnabled();
  await request.post(`/api/products/${product.id}/movements`, { data: { movement_type: 'OUT', quantity: 5 } });
  await dialog.getByRole('button', { name: 'Confirm issue', exact: true }).click();
  await expect(dialog.getByText('Requested quantity exceeds available stock', { exact: true })).toBeVisible();
  await expect(dialog.getByLabel('Quantity', { exact: true })).toHaveValue('8');
  await expect(dialog.getByLabel('Note (optional)', { exact: true })).toHaveValue('Keep my note');
  await expect(dialog.getByRole('button', { name: 'Confirm issue', exact: true })).toBeDisabled();
  await expect(dialog.getByText('Only 5 units are available. Enter 5 or fewer.', { exact: true })).toBeVisible();
});

test('product picker, activity and paginated product history remain connected', async ({ page, request }) => {
  const product = await createProduct(request, { name: 'Activity picker fixture' });
  for (let index = 0; index < 9; index++) await request.post(`/api/products/${product.id}/movements`, { data: { movement_type: 'IN', quantity: 1, note: `Receipt ${index}` } });
  await page.goto('/#/activity');
  await page.getByRole('button', { name: 'Record movement', exact: true }).click();
  const picker = page.getByRole('dialog', { name: 'Record a stock movement', exact: true });
  await picker.getByRole('textbox', { name: 'Find a product', exact: true }).fill(product.sku);
  await picker.getByRole('button').filter({ hasText: product.name }).click();
  const movement = page.getByRole('dialog', { name: 'Record stock movement', exact: true });
  await movement.getByLabel('Quantity', { exact: true }).fill('1');
  await movement.getByLabel('Note (optional)', { exact: true }).fill('Picker receipt');
  await movement.getByRole('button', { name: 'Confirm receipt', exact: true }).click();
  await expect(movement).not.toBeVisible();
  await expect(page.getByText('Picker receipt', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'View history', exact: true }).first().click();
  const history = page.getByRole('dialog', { name: 'Stock history', exact: true });
  await expect(history.locator('tbody tr')).toHaveCount(8);
  await history.getByRole('button', { name: 'Next movements page' }).click();
  await expect(history.locator('tbody tr')).toHaveCount(2);
});

test('mobile navigation, catalog cards and forms fit a narrow screen', async ({ page, request }) => {
  await createProduct(request, { name: 'Mobile layout fixture' });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#/overview');
  await expect(page.getByRole('heading', { name: 'Inventory overview', exact: true })).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: `../docs/screenshots/${evidencePrefix}-mobile-qa.png`, fullPage: true });
  await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
  await page.getByRole('link', { name: /Products/ }).click();
  await expect(page.getByRole('heading', { name: 'Your products', exact: true })).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Add product', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Add a product', exact: true });
  await expect(dialog).toBeVisible();
  expect(await dialog.evaluate((element) => element.getBoundingClientRect().width <= innerWidth)).toBe(true);
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
});

test('history loading can retry and the skip link preserves the current page', async ({ page, request }) => {
  const product = await createProduct(request, { name: 'History retry fixture' });
  await request.post(`/api/products/${product.id}/movements`, { data: { movement_type: 'IN', quantity: 2 } });
  await page.goto('/#/activity');
  const target = `**/api/products/${product.id}`;
  await page.route(target, (route) => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: { code: 'database_unavailable', message: 'History temporarily unavailable' } }) }));
  await page.getByRole('button', { name: 'View history', exact: true }).first().click();
  await expect(page.getByText('History temporarily unavailable', { exact: true })).toBeVisible();
  await page.unroute(target);
  await page.getByRole('button', { name: 'Try again', exact: true }).click();
  const history = page.getByRole('dialog', { name: 'Stock history', exact: true });
  await expect(history).toBeVisible();
  await history.getByRole('button', { name: 'Done', exact: true }).click();
  await page.getByRole('link', { name: 'Skip to content', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/#\/activity$/);
  await expect(page.locator('#main-content')).toBeFocused();
});
