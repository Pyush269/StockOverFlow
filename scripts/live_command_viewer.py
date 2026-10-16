"""Local-only viewer for a fixed set of real StockFlow verification commands.

The recorder starts commands through an authenticated localhost POST and sees
their stdout as it arrives. No arbitrary shell command or filesystem path is
accepted. This is an evidence tool, separate from the StockFlow application.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import threading

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.logs/walkthrough'
KUBE = ['kubectl', '--context', 'stockflow-eks-sydney', '--request-timeout=30s', '-n', 'stockflow']
COMMANDS = {
    'terraform': ['terraform', '-chdir=terraform', 'plan', '-no-color', '-input=false', '-parallelism=2', '-lock-timeout=30s'],
    'pods': KUBE + ['get', 'pods'],
    'services': KUBE + ['get', 'svc,ingress'],
    'compose': ['docker', 'compose', 'up', '--build', '-d', '--wait'],
    'pytest': ['docker', 'compose', '-f', 'compose.ci.yml', 'up', '--build', '--abort-on-container-exit', '--exit-code-from', 'backend-tests'],
}
TITLES = {'terraform': 'Live Terraform plan', 'pods': 'Live Kubernetes pods', 'services': 'Live Services and Ingress', 'compose': 'Docker Compose startup', 'pytest': 'Real PostgreSQL tests: pytest -v'}


@contextmanager
def viewer():
    token = secrets.token_urlsafe(24)
    lock = threading.Lock()
    report_path = WORK / 'live-commands.json'
    reports = json.loads(report_path.read_text()) if report_path.exists() else {}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path == '/health':
                self.send_response(200); self.end_headers(); self.wfile.write(b'UP'); return
            if not self.path.startswith('/?task=') or self.path.split('=', 1)[1] not in COMMANDS:
                self.send_error(404); return
            task = self.path.split('=', 1)[1]
            command = ' '.join(COMMANDS[task])
            page = r'''<!doctype html><html><meta charset="utf-8"><style>
            *{box-sizing:border-box}body{margin:0;background:#f6f5ef;color:#143c3a;font:23px/1.4 Arial}
            header{padding:28px 45px 12px}h1{font-size:36px;margin:0 0 8px}p{margin:0;color:#536a68}
            .bar{margin:12px 45px;display:flex;gap:20px;align-items:center}button{font:20px Arial;padding:12px 24px;background:#087f74;color:white;border:0;border-radius:6px}
            #state{font-weight:bold}#command{margin:15px 45px 0;padding:16px 22px;background:#173d3a;color:#effaf6;font:19px Consolas,monospace;overflow-wrap:anywhere}
            pre{margin:0 45px;padding:20px 22px;background:#102b2a;color:#effaf6;height:520px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;font:18px/1.4 Consolas,monospace}
            footer{padding:12px 45px;font:17px Arial;color:#536a68}
            </style><header><h1>TITLE</h1><p>Live command execution. Output below comes directly from the process.</p></header>
            <div class="bar"><button id="run">Run command</button><span id="state">Ready</span></div><div id="command">COMMAND</div><pre id="output"></pre><footer id="result">StockFlow verification • Sydney ap-southeast-2 • no infrastructure apply or destroy</footer>
            <script>
            const output=document.querySelector('#output'),state=document.querySelector('#state'),button=document.querySelector('#run');
            button.onclick=async()=>{button.disabled=true;state.textContent='Running';output.textContent='';
              try{const response=await fetch('/run',{method:'POST',headers:{'Content-Type':'application/json','X-Recording-Token':TOKEN},body:JSON.stringify({task:TASK})});if(!response.ok)throw Error('Command request failed');
                const reader=response.body.getReader(),decoder=new TextDecoder();let buffered='';for(;;){const {done,value}=await reader.read();if(done)break;buffered+=decoder.decode(value,{stream:true});let end;while((end=buffered.indexOf('\n'))>=0){const row=JSON.parse(buffered.slice(0,end));buffered=buffered.slice(end+1);if(row.text){output.textContent+=row.text;output.scrollTop=output.scrollHeight}if('exit_code'in row){state.textContent='Exit code: '+row.exit_code;state.style.color=row.exit_code===0?'#087f74':'#b62929';document.body.dataset.done=String(row.exit_code);document.querySelector('#result').textContent='Actual execution finished '+row.finished_at_utc}}}
              }catch(error){state.textContent=error.message;document.body.dataset.done='error'}};
            </script></html>'''
            page = page.replace('TITLE', html.escape(TITLES[task])).replace('COMMAND', html.escape(command)).replace('TOKEN', json.dumps(token)).replace('TASK', json.dumps(task))
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers(); self.wfile.write(page.encode('utf-8'))

        def do_POST(self):
            if self.path != '/run' or self.headers.get('X-Recording-Token') != token or self.headers.get('Content-Type') != 'application/json':
                self.send_error(403); return
            size = int(self.headers.get('Content-Length', '0'))
            if size > 100 or size <= 0:
                self.send_error(400); return
            task = json.loads(self.rfile.read(size)).get('task')
            if task not in COMMANDS or not lock.acquire(blocking=False):
                self.send_error(409); return
            self.send_response(200); self.send_header('Content-Type', 'application/x-ndjson; charset=utf-8'); self.send_header('Cache-Control', 'no-store'); self.end_headers()
            began = datetime.now(timezone.utc).isoformat()
            process = None
            lines = []
            def send(value):
                self.wfile.write((json.dumps(value) + '\n').encode('utf-8')); self.wfile.flush()
            try:
                env = dict(os.environ, AWS_PROFILE='stockflow', AWS_REGION='ap-southeast-2', GOMAXPROCS='2', NO_COLOR='1', BUILDKIT_PROGRESS='plain')
                process = subprocess.Popen(COMMANDS[task], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', bufsize=1)
                timeout = threading.Timer(600, process.kill); timeout.start()
                try:
                    for line in process.stdout:
                        lines.append(line); send({'text': line})
                    code = process.wait()
                finally:
                    timeout.cancel()
                finished = datetime.now(timezone.utc).isoformat()
                reports[task] = {'command': COMMANDS[task], 'started_at_utc': began, 'finished_at_utc': finished, 'exit_code': code}
                (WORK / ('live-' + task + '.txt')).write_text(''.join(lines), encoding='utf-8')
                (WORK / 'live-commands.json').write_text(json.dumps(reports, indent=2) + '\n')
                send({'exit_code': code, 'finished_at_utc': finished})
            except (BrokenPipeError, ConnectionResetError):
                if process and process.poll() is None:
                    process.terminate(); process.wait(timeout=10)
            finally:
                lock.release()

    server = ThreadingHTTPServer(('127.0.0.1', 8765), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        yield 'http://127.0.0.1:8765'
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=10)
