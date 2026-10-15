// Called by verify-monitoring.py. Credentials arrive through stdin, never CLI args.
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

let input = '';
for await (const chunk of process.stdin) input += chunk;
const settings = JSON.parse(input);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
process.env.PLAYWRIGHT_BROWSERS_PATH ||= path.join(root, '.playwright-browsers');
const { chromium } = await import('../frontend/node_modules/playwright/index.mjs');
const browser = await chromium.launch({ headless: true, channel: 'chromium' });
try {
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 } });
  const page = await context.newPage();
  await page.goto('http://127.0.0.1:3002/login');
  await page.getByLabel(/email or username/i).fill(settings.username);
  await page.getByLabel(/^password$/i).fill(settings.password);
  await page.getByRole('button', { name: /^log in$/i }).click();
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 30000 });
  await page.goto(`http://127.0.0.1:3002/d/stockflow-overview?orgId=1&var-datasource=prometheus&var-namespace=${encodeURIComponent(settings.namespace)}&from=now-15m&to=now`);
  await page.getByText('API request rate', { exact: true }).waitFor();
  await page.getByText('Backend ready replicas', { exact: true }).waitFor();
  await page.waitForTimeout(10000);
  if (await page.getByText('No data', { exact: true }).count()) throw new Error('A Grafana panel has no data');
  await mkdir(path.join(root, 'docs/screenshots'), { recursive: true });
  await page.screenshot({ path: path.join(root, 'docs/screenshots/stockflow-grafana-local.png'), fullPage: true });
  console.log('PASS: authenticated Grafana dashboard rendered with live panels');
  await context.close();
} finally {
  await browser.close();
}
