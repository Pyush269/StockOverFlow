// Read the local ArgoCD password through stdin; use a fresh isolated browser context.
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
  // Local port-forward uses the ArgoCD installation's self-signed certificate.
  const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1600, height: 1000 } });
  const response = await context.request.post('https://127.0.0.1:8443/api/v1/session', { data: { username: 'admin', password: settings.password } });
  if (!response.ok()) throw new Error('Local ArgoCD authentication failed');
  const { token } = await response.json();
  await context.addCookies([{ name: 'argocd.token', value: token, domain: '127.0.0.1', path: '/', secure: true, httpOnly: false, sameSite: 'Lax' }]);
  const page = await context.newPage();
  await page.goto('https://127.0.0.1:8443/applications/argocd/stockflow-local');
  await page.getByText('Healthy', { exact: true }).first().waitFor({ timeout: 30000 });
  await page.getByText('Synced', { exact: true }).first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(root, 'docs/screenshots/stockflow-argocd-local.png'), fullPage: true });
  console.log('PASS: local ArgoCD UI shows Healthy and Synced');
  await context.close();
} finally {
  await browser.close();
}
