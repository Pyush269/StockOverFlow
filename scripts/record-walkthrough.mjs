// Fresh project browser. Never attaches to the user's Chrome profile.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
let input='';for await(const chunk of process.stdin)input+=chunk;
const credentials=JSON.parse(input); input='';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const work=path.join(root,'.logs/walkthrough');
const screens=path.join(root,'docs/screenshots');
process.env.PLAYWRIGHT_BROWSERS_PATH ||= path.join(root,'.playwright-browsers');
const {chromium}=await import('../frontend/node_modules/playwright/index.mjs');
const browser=await chromium.launch({headless:true,channel:'chromium'});
const origin=JSON.parse(await readFile(path.join(root,'docs/CLOUD_RUNTIME_VERIFICATION.json'),'utf8')).origin;
const evidence=JSON.parse(await readFile(path.join(work,'commands.json'),'utf8'));
const esc=v=>String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const proof={recorded_at_utc:new Date().toISOString(),origin,segments:[],checks:[]};
const viewport={width:1600,height:900};
let context,page,began,segment;
async function start(name){
  context=await browser.newContext({viewport,ignoreHTTPSErrors:true,recordVideo:{dir:path.join(work,name),size:viewport}});
  segment={name,chapters:[]};began=Date.now();page=await context.newPage();
}
async function mark(title,caption){segment.chapters.push({seconds:Math.round((Date.now()-began)/1000),title,caption});console.log(title);}
async function label(text){
  await page.evaluate(text=>{document.querySelector('#walkthrough-caption')?.remove();const e=document.createElement('div');e.id='walkthrough-caption';e.textContent=text;Object.assign(e.style,{position:'fixed',left:'0',right:'0',bottom:'0',padding:'17px 32px',background:'#102b2af5',color:'#fff',font:'22px/1.4 Arial,sans-serif',zIndex:'2147483647',pointerEvents:'none'});document.body.append(e);},text);
}
async function card(title,caption,body,source='Actual StockFlow source or captured command output'){
  await mark(title,caption);await page.goto('about:blank');
  await page.setContent(`<html><style>*{box-sizing:border-box}body{margin:0;background:#f6f5ef;color:#143c3a;font:25px/1.45 Arial}main{padding:42px 60px}h1{font-size:40px;margin:0 0 12px}p{color:#536a68;margin:0 0 24px}pre{background:#102b2a;color:#effaf6;border-radius:8px;padding:24px;font:19px/1.45 Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-height:645px;overflow:auto}footer{position:fixed;bottom:0;left:0;right:0;padding:12px 60px;font:18px Arial;background:#e8eee5;color:#536a68}</style><main><h1>${esc(title)}</h1><p>${esc(caption)}</p><pre>${esc(body)}</pre></main><footer>${esc(source)}</footer></html>`);
}
async function shot(name){await page.screenshot({path:path.join(screens,name)});}
async function finish(){segment.video=path.relative(root,await page.video().path());segment.seconds=Math.round((Date.now()-began)/1000);await context.close();proof.segments.push(segment);await writeFile(path.join(work,'recording.json'),JSON.stringify(proof,null,2)+'\n');}
try{
  await mkdir(screens,{recursive:true});
  await start('application-code');
  await mark('Live application','Real AWS ALB; no mocked API responses');
  await page.goto(origin);await page.getByRole('heading',{name:'Inventory overview'}).waitFor();
  await label('Live AWS application: inventory dashboard, low-stock alerts, and movement history.');await sleep(8000);
  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:/^Products/}).click();
  await page.getByRole('textbox',{name:'Search products',exact:true}).waitFor();
  await label('Live product catalog: the React frontend reads inventory from the FastAPI/PostgreSQL backend.');await shot('stockflow-catalog-walkthrough.png');await sleep(7000);
  proof.checks.push({application:'live dashboard and catalog rendered'});
  await card('Codebase structure','Each layer has a separate responsibility',`backend/app/       FastAPI routes, schemas, inventory service\nbackend/alembic/   Versioned PostgreSQL schema\nbackend/tests/     Real database tests and concurrency checks\nfrontend/src/      React screens and API client\nDockerfiles        Non-root API and multi-stage UI image\n.github/workflows/ Tests, image scans, SHA publication\nterraform/         VPC, EKS, private worker, scoped identities\nhelm/stockflow/    Application templates and release values\nargocd/            GitOps application and project\nmonitoring/        Prometheus values and Grafana dashboard`);await sleep(14000);
  const service=(await readFile(path.join(root,'backend/app/services/inventory.py'),'utf8')).split(/\r?\n/);
  await card('Transactional inventory service','Source excerpt: backend/app/services/inventory.py',service.slice(service.findIndex(l=>l.startsWith('def record_movement')),service.findIndex(l=>l.startsWith('    logger.info'))).join('\n'));await sleep(16000);
  await page.locator('pre').evaluate(e=>e.scrollTop=e.scrollHeight);await sleep(7000);
  await card('Tests and containers','Actual test output from the recorded successful pipeline',JSON.parse(await readFile(path.join(root,'.logs/pipeline-video/job-116863979627.json'),'utf8')).excerpt+'\n\n'+(await readFile(path.join(root,'frontend/Dockerfile'),'utf8')));await shot('stockflow-tests-and-docker.png');await sleep(14000);
  await finish();
  await start('operations');
  const plan=await readFile(path.join(work,'plan.txt'),'utf8');
  await card('Terraform plan','Actual read-only plan output; infrastructure already deployed',plan);await shot('stockflow-terraform-plan.png');await sleep(14000);
  for(const [file,title] of [['stockflow-aws-eks-console.png','AWS Console: EKS'],['stockflow-aws-vpc-console.png','AWS Console: VPC']]){
    try{
      const bytes=await readFile(path.join(screens,file));
      await mark(title,'Actual AWS Console capture');await page.goto('about:blank');await page.setContent(`<html style="margin:0;background:#101b22"><body style="margin:0"><img src="data:image/png;base64,${bytes.toString('base64')}" style="width:1600px;height:825px;object-fit:contain"></body></html>`);await label(title+' — actual project resources in Sydney (ap-southeast-2).');await sleep(14000);
    }catch(error){if(error.code!=='ENOENT')throw error;proof.checks.push({missing_required_console_capture:file});}
  }
  const argo=await context.request.post('https://127.0.0.1:8443/api/v1/session',{data:{username:'admin',password:credentials.argocd_password}});assert(argo.ok());
  const {token}=await argo.json();await context.addCookies([{name:'argocd.token',value:token,domain:'127.0.0.1',path:'/',secure:true,httpOnly:false,sameSite:'Lax'}]);
  await mark('ArgoCD live application','Synced and Healthy; Git controls the deployed image values');
  await page.goto('https://127.0.0.1:8443/applications/argocd/stockflow');await page.getByText('Healthy',{exact:true}).first().waitFor({timeout:30000});await page.getByText('Synced',{exact:true}).first().waitFor();
  await label('Live EKS ArgoCD: Synced and Healthy. Actions publishes images; a values commit promotes a release.');await shot('stockflow-argocd-walkthrough.png');await sleep(16000);
  await card('GitOps delivery','The repository values select the deployed image; ArgoCD reconciles Git with EKS.', 'Repository: https://github.com/Pyush269/StockOverFlow\nApplication: stockflow\nSync: Synced   Health: Healthy\nObserved Git revision: '+evidence.argocd_revision+'\n\nDeployed images:\n'+evidence.images.join('\n')+'\n\nPublishing to GHCR does not change this release automatically.\nA release-values commit promotes a published SHA; reverting it rolls back.');await sleep(12000);
  for(const [key,title] of [['pods','Kubernetes pods'],['services','Services and Ingress']]){
    const c=evidence.commands[key];await card(title,'Actual output captured '+evidence.captured_at_utc,c.command+'\n\n'+c.output);await shot('stockflow-'+key+'-terminal.png');await sleep(12000);
  }
  const metrics=await(await context.request.get('http://127.0.0.1:8001/metrics')).text();assert(metrics.includes('http_requests_total'));
  await card('Application metrics','Actual backend /metrics response through a localhost port-forward',metrics.split('\n').filter(l=>/http_requests_total|http_request_duration_seconds_(count|sum)/.test(l)).slice(0,14).join('\n'));await shot('stockflow-metrics-output.png');await sleep(12000);
  const targets=await(await context.request.get('http://127.0.0.1:9090/api/v1/targets')).json();
  const appTargets=targets.data.activeTargets.filter(t=>t.labels.namespace==='stockflow'&&t.labels.service==='stockflow-stockflow-backend');assert(appTargets.length>=2&&appTargets.every(t=>t.health==='up'&&!t.lastError));
  await mark('Prometheus live Targets','Actual scrape targets are UP');await page.goto('http://127.0.0.1:9090/targets');await page.getByText(/stockflow-stockflow-backend/).first().waitFor({timeout:30000});
  const targetText=page.getByText(/stockflow-stockflow-backend/).first();await targetText.scrollIntoViewIfNeeded();
  await label(`Live Prometheus Targets: ${appTargets.length} StockFlow backend targets are UP; no scrape errors.`);await shot('stockflow-prometheus-targets-cloud.png');await sleep(18000);
  proof.checks.push({prometheus_targets_up:appTargets.length});
  const login=await context.request.post('http://127.0.0.1:3002/login',{data:{user:credentials.grafana_user,password:credentials.grafana_password}});assert(login.ok());
  await mark('Grafana live dashboard','Live application request, latency, and availability panels');
  await page.goto('http://127.0.0.1:3002/d/stockflow-overview?orgId=1&var-datasource=prometheus&var-namespace=stockflow&from=now-30m&to=now');await page.getByText('API request rate',{exact:true}).waitFor({timeout:30000});await sleep(10000);
  assert.equal(await page.getByText('No data',{exact:true}).count(),0);
  await label('Live Grafana dashboard: request rate, latency, errors, backend replicas, and process metrics.');await shot('stockflow-grafana-walkthrough.png');await sleep(16000);
  await finish();
}finally{if(context)await context.close().catch(()=>{});await browser.close();}
console.log('Actual silent application/code and operations recordings saved.');
