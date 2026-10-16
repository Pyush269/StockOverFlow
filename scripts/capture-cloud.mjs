// Actual public ALB frontend evidence, using an isolated project QA browser.
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const { origin } = JSON.parse(await readFile(path.join(root, '.logs/cloud-runtime.json'), 'utf8'));
const url = new URL(origin);
if (!url.hostname.endsWith('.ap-southeast-2.elb.amazonaws.com') || url.protocol !== 'http:') throw new Error('Expected the verified Sydney ALB origin');
process.env.PLAYWRIGHT_BROWSERS_PATH ||= path.join(root, '.playwright-browsers');
const { chromium } = await import('../frontend/node_modules/playwright/index.mjs');
const browser = await chromium.launch({ headless: true, channel: 'chromium' });
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(origin);
  await page.getByRole('heading', { name: 'Inventory overview' }).waitFor({ timeout: 30000 });
  await page.getByText('AWS capstone inventory proof', { exact: true }).first().waitFor({ timeout: 30000 });
  const response = await context.request.get(origin + '/api/dashboard');
  if (response.status() !== 200 || errors.length) throw new Error('Public frontend/API browser verification failed');
  await page.screenshot({ path: path.join(root, 'docs/screenshots/stockflow-cloud-overview.png'), fullPage: true });
  await page.getByRole('link', { name: 'Products', exact: true }).click();
  await page.getByRole('textbox', { name: 'Search products', exact: true }).waitFor();
  await page.screenshot({ path: path.join(root, 'docs/screenshots/stockflow-cloud-products.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(origin);
  await page.getByRole('heading', { name: 'Inventory overview' }).waitFor();
  await page.screenshot({ path: path.join(root, 'docs/screenshots/stockflow-cloud-mobile.png'), fullPage: true });
  console.log('PASS: actual public ALB overview, catalog, mobile UI, and dashboard API');
  await context.close();
} finally {
  await browser.close();
}
