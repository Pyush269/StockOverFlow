import { chromium } from '@playwright/test';
import { mkdir } from 'node:fs/promises';

await mkdir('../docs/screenshots', { recursive: true });
const browser = await chromium.launch({ channel: 'chromium', headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('http://127.0.0.1:5173/#/overview');
  await page.getByRole('heading', { name: 'Inventory overview', exact: true }).waitFor();
  await page.getByText('Inventory connected', { exact: true }).waitFor({ state: 'attached' });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: '../docs/screenshots/frontend-overview.png', fullPage: true });
  await page.goto('http://127.0.0.1:5173/#/products');
  await page.locator('.catalog-panel tbody tr').first().waitFor();
  await page.screenshot({ path: '../docs/screenshots/frontend-products.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('http://127.0.0.1:5173/#/overview');
  await page.getByRole('heading', { name: 'Inventory overview', exact: true }).waitFor();
  await page.getByText('Inventory connected', { exact: true }).waitFor({ state: 'attached' });
  await page.screenshot({ path: '../docs/screenshots/frontend-mobile.png', fullPage: true });
  if (errors.length) throw new Error(errors.join('\n'));
  console.log('Read-only development preview captured: desktop overview, catalog, mobile overview. No page errors.');
} finally { await browser.close(); }
