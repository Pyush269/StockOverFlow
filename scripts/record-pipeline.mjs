// Record a real public CI run; GitHub credentials stay in the separate API monitor.
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const work = path.join(root, '.logs/pipeline-video');
await mkdir(work, {recursive:true});
process.env.PLAYWRIGHT_BROWSERS_PATH ||= path.join(root, '.playwright-browsers');
const {chromium} = await import('../frontend/node_modules/playwright/index.mjs');
const browser = await chromium.launch({headless:true,channel:'chromium'});
const context = await browser.newContext({viewport:{width:1600,height:900},recordVideo:{dir:path.join(work,'raw'),size:{width:1600,height:900}}});
const page = await context.newPage();
const timeline = [];
const began = Date.now();
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const escape = value => String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
async function mark(chapter, note) {
  timeline.push({seconds:Math.round((Date.now()-began)/1000),chapter,note});
  await writeFile(path.join(work,'timeline.json'),JSON.stringify(timeline,null,2)+'\n');
  console.log(chapter, note);
}
async function card(title, subtitle, content, source='StockFlow | Pyush269/StockOverFlow') {
  await page.goto('about:blank');
  await page.setContent(`<!doctype html><html><head><style>
    *{box-sizing:border-box}body{margin:0;background:#f6f5ef;color:#143c3a;font:24px/1.5 Arial,sans-serif}
    main{padding:48px 66px}h1{font-size:42px;margin:0 0 10px}p{margin:0 0 22px;color:#536a68}
    pre{margin:20px 0 0;padding:26px;background:#102b2a;color:#effaf6;font:20px/1.5 Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-height:650px;overflow:hidden;border-radius:8px}
    footer{position:fixed;bottom:0;width:100%;background:#e8eee5;padding:12px 66px;font-size:18px;color:#536a68}
    .hero{margin:90px 0 40px;font-size:36px;color:#087f74}.small{font-size:21px}
  </style></head><body><main><h1>${escape(title)}</h1><p>${escape(subtitle)}</p>${content}</main><footer>${escape(source)}</footer></body></html>`);
}
async function readJson(name) {
  try {return JSON.parse(await readFile(path.join(work,name),'utf8'));}
  catch (error) {if(error.code==='ENOENT' || error instanceof SyntaxError) return null; throw error;}
}
let finalRun;
try {
  await mark('Introduction','Silent recording of an actual push-to-main pipeline.');
  await card('StockFlow: working CI pipeline','Silent walkthrough | 16 October 2026',`<div class="hero">Tests → Build and scan → Publish to GHCR</div><p>Real GitHub Actions run, from a new push through the final result.</p><p class="small">Add your own narration using demo/PIPELINE_NARRATION.md.</p>`);
  await pause(8000);
  const source = await readFile(path.join(root,'.github/workflows/ci.yml'),'utf8');
  const lines = source.split(/\r?\n/);
  const excerpts = [
    ['Tests are the first gate','Source excerpt: .github/workflows/ci.yml',lines.slice(lines.findIndex(l=>l.startsWith('      - name: Upgrade empty database')),lines.findIndex(l=>l.startsWith('      - name: Save test evidence')))],
    ['Build once, then scan','Source excerpt: strict HIGH/CRITICAL image gates',lines.slice(lines.findIndex(l=>l.startsWith('      - name: Build each image')),lines.findIndex(l=>l.startsWith('      - name: Save verified release archive')))],
    ['Publish the scanned image bytes','Source excerpt: publish job depends on tests and images',lines.slice(lines.findIndex(l=>l.startsWith('  publish:')),lines.findIndex(l=>l.startsWith('      - name: Verify archive')))],
  ];
  for (const [title,subtitle,excerpt] of excerpts) {
    await mark(title,subtitle);
    await card(title,subtitle,`<pre>${escape(excerpt.join('\n'))}</pre>`);
    await pause(11000);
  }
  await card('Trigger the pipeline','Waiting for the real git push output', '<p class="hero">Next: push the recording helper to main.</p><p>The recording follows the run created by that exact commit.</p>');
  await writeFile(path.join(work,'ready.json'),JSON.stringify({ready:true}));
  const triggerDeadline = Date.now()+180000;
  let trigger;
  while (!(trigger = await readJson('trigger.json'))) {
    if (Date.now()>triggerDeadline) throw new Error('Timed out waiting for the real push/run metadata');
    await pause(1000);
  }
  if (!/^[a-f0-9]{40}$/.test(trigger.sha) || !trigger.run.html_url.startsWith('https://github.com/Pyush269/StockOverFlow/actions/runs/')) throw new Error('Unexpected recording target');
  await mark('Actual git push',`Source SHA ${trigger.sha}`);
  await card('A real push to main','Captured command output, followed by the corresponding GitHub run',`<pre>${escape(trigger.push_output)}\n\nSource SHA: ${escape(trigger.sha)}\nRun: ${escape(trigger.run.html_url)}</pre>`);
  await pause(12000);
  await mark('Live GitHub Actions run',trigger.run.html_url);
  await page.goto(trigger.run.html_url,{waitUntil:'domcontentloaded',timeout:45000});
  await page.getByText('Triggered via push',{exact:false}).first().waitFor({timeout:30000});
  await page.screenshot({path:path.join(work,'run-start.png')});
  const runDeadline = Date.now()+25*60*1000;
  let previous = '';
  for (;;) {
    const state = await readJson('status.json');
    if (state?.run.head_sha === trigger.sha) {
      const signature = JSON.stringify(state.jobs.map(j=>[j.name,j.status,j.conclusion]));
      if (signature!==previous) {
        await mark('Pipeline progress',state.jobs.map(j=>`${j.name}: ${j.conclusion||j.status}`).join(' | '));
        previous = signature;
      }
      if (state.run.status==='completed') {finalRun=state;break;}
    }
    if (Date.now()>runDeadline) throw new Error('CI did not finish within the recording window');
    await pause(12000);
    await page.reload({waitUntil:'domcontentloaded',timeout:45000});
  }
  await page.reload({waitUntil:'domcontentloaded',timeout:45000});
  await pause(5000);
  await page.screenshot({path:path.join(work,'run-complete.png')});
  await mark('Final GitHub result',`Conclusion: ${finalRun.run.conclusion}`);
  await pause(15000);
  if (finalRun.run.conclusion!=='success') throw new Error('The recorded CI run failed; inspect its real logs');
  await page.getByRole('heading',{name:'Artifacts',exact:true}).scrollIntoViewIfNeeded().catch(()=>{});
  await pause(8000);
  for (const job of finalRun.jobs) {
    const details = await readJson(`job-${job.id}.json`);
    if (!details) throw new Error('Missing actual job evidence: '+job.name);
    await mark(job.name,'Actual GitHub Actions job output');
    await card(job.name,'Actual completed job output, retrieved through the GitHub API',`<pre>${escape(details.excerpt)}</pre>`,job.html_url);
    await pause(18000);
  }
  await mark('Pipeline complete','All three jobs succeeded; both scanned SHA-tagged images were published.');
  await card('Pipeline complete','All three jobs succeeded',`<div class="hero">Tests passed. Security gates passed. Images published.</div><pre>Commit: ${escape(trigger.sha)}\n\n${escape(finalRun.jobs.map(j=>j.name+' — '+j.conclusion).join('\n'))}\n\n${escape(trigger.run.html_url)}</pre>`);
  await pause(12000);
  await writeFile(path.join(work,'recording-result.json'),JSON.stringify({run_url:trigger.run.html_url,source_sha:trigger.sha,conclusion:finalRun.run.conclusion,seconds:Math.round((Date.now()-began)/1000),silent:true,timeline},null,2)+'\n');
} finally {
  await context.close();
  await browser.close();
}
console.log('Recording complete; raw video is in .logs/pipeline-video/raw');
