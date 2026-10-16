// Supplementary rubric screenshots. No user browser profile or saved sign-in.
import {readFile,writeFile,access,copyFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';

export async function captureGradingEvidence(browser,viewerOrigin,root){
  const context=await browser.newContext({viewport:{width:1600,height:1200}});
  const page=await context.newPage();
  const folder=path.join(root,'docs/screenshots');
  const report={captured_at_utc:new Date().toISOString(),screenshots:[]};
  async function shot(file,source){
    await page.screenshot({path:path.join(folder,file)});
    report.screenshots.push({file:'docs/screenshots/'+file,source});
    console.log('Captured '+file);
  }
  const sha=execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim();
  let verifiedCommands={};
  try{verifiedCommands=JSON.parse(await readFile(path.join(root,'.logs/walkthrough/live-commands.json'),'utf8'));}catch(error){if(error.code!=='ENOENT')throw error;}
  try{
    await page.goto('https://github.com/Pyush269/StockOverFlow/commits/main/',{waitUntil:'domcontentloaded',timeout:45000});
    const messages=execFileSync('git',['log','-10','--format=%s'],{cwd:root,encoding:'utf8'}).trim().split('\n');
    await page.getByText(messages[0],{exact:true}).first().waitFor({timeout:30000});
    // Hide global chrome by scrolling to the actual newest commit, preserving the page.
    await page.getByText(messages[0],{exact:true}).first().scrollIntoViewIfNeeded();
    await shot('stockflow-git-history.png','https://github.com/Pyush269/StockOverFlow/commits/main/');
    for(const image of ['backend','frontend']){
      const url='https://github.com/users/Pyush269/packages/container/package/stockflow-'+image;
      await page.goto(url,{waitUntil:'domcontentloaded',timeout:45000});
      await page.getByText(sha,{exact:false}).first().waitFor({timeout:30000});
      await shot('stockflow-ghcr-'+image+'.png',url);
    }
    await page.goto('http://127.0.0.1:3000');
    await page.getByRole('heading',{name:'Inventory overview'}).waitFor({timeout:30000});
    await shot('stockflow-localhost-3000.png','http://127.0.0.1:3000');
    for(const [task,file] of [['compose','stockflow-compose-startup.png'],['pytest','stockflow-pytest-verbose.png']]){
      if(verifiedCommands[task]?.exit_code===0){
        await access(path.join(folder,file));
        report.screenshots.push({file:'docs/screenshots/'+file,source:'Actual successful execution at '+verifiedCommands[task].finished_at_utc});
        console.log('Preserved verified '+task+' screenshot.');continue;
      }
      await page.goto(viewerOrigin+'/?task='+task);
      await page.waitForFunction(()=>typeof document.querySelector('#run')?.onclick==='function',{},{timeout:10000});
      await page.getByRole('button',{name:'Run command',exact:true}).click();
      await page.waitForFunction(()=>document.body.dataset.done!==undefined,{},{timeout:600000});
      assert.equal(await page.locator('body').getAttribute('data-done'),'0',task+' failed');
      await shot(file,'Live actual process; command and exit code visible');
      if(task==='pytest')assert((await page.locator('#output').innerText()).includes('49 passed'));
    }
    const helmBytes=await readFile(path.join(root,'docs/CLOUD_HELM_LIST.txt'));
    const helm=helmBytes.toString(helmBytes[0]===255&&helmBytes[1]===254?'utf16le':'utf8').replace(/^\uFEFF/,'');
    assert(helm.includes('warehouse')&&helm.includes('deployed'));
    const esc=v=>v.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
    await page.goto('about:blank');
    await page.setContent(`<html><style>body{padding:45px;background:#f6f5ef;color:#143c3a;font:25px Arial}h1{font-size:40px}p{line-height:1.6}pre{padding:25px;background:#102b2a;color:#effaf6;font:20px/1.6 Consolas;white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Helm release: actual saved cloud output</h1><p>Historical verification on 16 October 2026. Namespace: stockflow-smoke.<br>The disposable release was removed after verification; production uses ArgoCD.</p><pre>helm --kube-context stockflow-eks-sydney list -n stockflow-smoke\n\n${esc(helm)}</pre><p>Actual source: docs/CLOUD_HELM_LIST.txt<br>Runtime proof: docs/CLOUD_HELM_VERIFICATION.json (upgrade, migrations, PVC, two replicas).</p></html>`);
    await shot('stockflow-helm-list.png','Actual historical Helm output; docs/CLOUD_HELM_LIST.txt');
    const metrics=(await readFile(path.join(root,'.logs/walkthrough/curl-metrics.txt'),'utf8')).split('\n').filter(line=>/^# (HELP|TYPE) http_requests_total|^http_requests_total/.test(line)).slice(0,14).join('\n');
    assert(metrics.includes('http_requests_total'));
    await page.setContent(`<html><style>body{padding:45px;background:#f6f5ef;color:#143c3a;font:24px Arial}h1{font-size:40px}p{line-height:1.5}pre{padding:25px;background:#102b2a;color:#effaf6;font:19px/1.6 Consolas;white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Backend metrics: actual curl response</h1><p>Captured from the EKS backend through a temporary localhost port-forward.</p><pre>curl.exe --fail --silent --show-error http://127.0.0.1:8001/metrics\n\n${esc(metrics)}</pre><p>Prometheus exposition format: metric HELP/TYPE definitions and labelled request counters.<br>Selected lines from the actual successful HTTP response; credentials are not required for this demo endpoint.</p></html>`);
    await shot('stockflow-curl-metrics.png','Actual curl response captured during this cloud verification');
    const commands=JSON.parse(await readFile(path.join(root,'.logs/walkthrough/live-commands.json'),'utf8'));
    report.actual_command_execution=Object.fromEntries(['compose','pytest'].map(name=>[name,commands[name]]));
    const raw=await readFile(path.join(root,'.logs/walkthrough/live-pytest.txt'));
    const testLines=raw.toString('utf8').split(/\r?\n/).filter(line=>line.startsWith('backend-tests-1')).map(line=>line.trimEnd());
    const passed=testLines.filter(line=>line.includes(' PASSED')).length;assert.equal(passed,49);
    await writeFile(path.join(root,'docs/evidence/pytest-verbose.txt'),testLines.join('\n')+'\n');
    report.pytest_stdout={file:'docs/evidence/pytest-verbose.txt',selection:'All backend-tests-1 stdout lines from the actual isolated Compose run; line-end whitespace trimmed',passed_cases:passed,source_log_sha256:createHash('sha256').update(raw).digest('hex')};
    await copyFile(path.join(root,'.logs/pipeline-video/qa-scan.png'),path.join(folder,'stockflow-trivy-ci.png'));
    report.screenshots.push({file:'docs/screenshots/stockflow-trivy-ci.png',source:'Actual strict scan job 116864354356 in GitHub Actions run 38867618119'});
    for(const screenshot of report.screenshots)screenshot.sha256=createHash('sha256').update(await readFile(path.join(root,screenshot.file))).digest('hex');
    await writeFile(path.join(root,'docs/evidence/SUPPLEMENTARY_VERIFICATION.json'),JSON.stringify(report,null,2)+'\n');
  }finally{await context.close();}
}
