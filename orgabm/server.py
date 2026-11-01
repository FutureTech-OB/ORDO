"""Local-only prototype. Browser executes free rule engines; live APIs use the CLI."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlparse
from .experiment import run
from .organization import validate_config
from .personas import parse_personas
from .workforce import build_workforce, workforce_metadata
from .organization import memberships
from .placement import preview_assignment

ROOT = Path(__file__).resolve().parent.parent
RUN_LOCK = threading.Lock()
WORKFLOW_SERVICE = None


def workflow_service():
    global WORKFLOW_SERVICE
    with RUN_LOCK:
        if WORKFLOW_SERVICE is None:
            from .mcp_server import ExperimentService
            WORKFLOW_SERVICE = ExperimentService(ROOT/'runs'/'browser-workflow')
        return WORKFLOW_SERVICE


def browser_workflow_preview(plan):
    from .plans import expand_plan
    if not isinstance(plan,dict) or plan.get('scenario')!='task_workflow':
        raise ValueError('Browser workflow runs require task_workflow with free rules.')
    expanded=expand_plan(plan)
    if expanded['decision'].get('provider','rule')!='rule':
        raise ValueError('Browser workflow runs require free rules.')
    if (expanded['worlds']>6 or expanded['decisions']>30000 or
        any(c['agents']>80 or len(c['tasks'])>200 or c['rounds']>40 for c in expanded['configs'])):
        raise ValueError('Browser limits: 6 worlds, 80 members, 200 tasks, 40 ticks and 30,000 decision opportunities. Larger experiments use CLI/MCP.')
    return expanded


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, mime='application/json; charset=utf-8'):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'")
        self.end_headers()
        self.wfile.write(body)

    def trusted_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

    def do_GET(self):
        if not self.trusted_host():
            return self.send(403, {'error': 'Local host only'})
        path = urlparse(self.path).path
        files = {'/': ('web/index.html', 'text/html; charset=utf-8'),
                 '/workflow': ('web/workflow.html', 'text/html; charset=utf-8'),
                 '/workflow.js': ('web/workflow.js', 'text/javascript; charset=utf-8'),
                 '/workflow.css': ('web/workflow.css', 'text/css; charset=utf-8'),
                 '/app.js': ('web/app.js', 'text/javascript; charset=utf-8'),
                 '/style.css': ('web/style.css', 'text/css; charset=utf-8'),
                 '/api/persona-example': ('examples/persona_organization.json', 'application/json; charset=utf-8'),
                 '/api/assignment-example': ('examples/persona_assignment.json', 'application/json; charset=utf-8'),
                 '/api/archive': ('examples/archived_pilot.json', 'application/json; charset=utf-8')}
        if path == '/api/health':
            from . import __version__
            return self.send(200, dict(status='ok', version=__version__, live_api_enabled=False))
        if path == '/api/workflow/templates':
            from .templates import workflow_plan
            return self.send(200,{name:workflow_plan(name) for name in ['functional_hierarchy','delegated_teams','authority_comparison','review_capacity_comparison','memory_permissions']})
        if path.startswith('/api/workflow/status/'):
            try:
                return self.send(200,workflow_service().get(path.rsplit('/',1)[-1]))
            except (ValueError,FileNotFoundError):
                return self.send(404,{'error':'Workflow run not found.'})
        if path not in files:
            return self.send(404, {'error': 'Not found'})
        name, mime = files[path]
        self.send(200, (ROOT/name).read_bytes(), mime)

    def do_POST(self):
        if not self.trusted_host():
            return self.send(403, {'error': 'Local host only'})
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'):
            return self.send(403, {'error': 'Origin rejected'})
        if self.path not in ['/api/run', '/api/personas/import', '/api/personas/assignment-preview', '/api/workforce/preview',
                             '/api/workflow/preview','/api/workflow/start','/api/workflow/inspect','/api/workflow/memory-preview']:
            return self.send(404, {'error': 'Not found'})
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.send(415, {'error': 'JSON required'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 2_000_000:
                raise ValueError('Request too large or empty')
            body = json.loads(self.rfile.read(length))
            if self.path == '/api/workflow/memory-preview':
                if not isinstance(body,dict) or set(body)-{'plan','agent','round_no'}:
                    raise ValueError('Memory preview requires plan, agent and round_no.')
                expanded=browser_workflow_preview(body.get('plan'))
                c=expanded['configs'][0]
                from .workflow import labels
                from .memory import MemoryForest
                agent,round_no=body.get('agent'),body.get('round_no')
                if type(agent) is not int or not 0<=agent<c['agents'] or type(round_no) is not int or not 1<=round_no<=c['rounds']:
                    raise ValueError('Select a member and round within the plan.')
                if c['memory'] is None:
                    return self.send(200,dict(view={'items':[]},audit=None,note='No memory configured in the first condition.'))
                forest=MemoryForest(c['memory'],build_workforce(c,labels(c)))
                view,audit=forest.observe(agent,round_no)
                return self.send(200,dict(view=view,audit=audit,note='Researcher preview for the first condition. Only view enters an agent question; audit is researcher-only.'))
            if self.path in ('/api/workflow/preview','/api/workflow/start'):
                expanded=browser_workflow_preview(body)
                if self.path.endswith('/preview'):
                    from .workflow import labels
                    c=expanded['configs'][0]
                    return self.send(200,dict(**{k:v for k,v in expanded.items() if k!='configs'},
                        roster=build_workforce(c,labels(c)),tasks=c['tasks'],phases=['proposal']+[f'review_{i}' for i in range(c['review_capacity'])],
                        note='Preview roster/tasks describe the first condition; all conditions are in the plan.'))
                return self.send(200,workflow_service().start(body))
            if self.path == '/api/workflow/inspect':
                if not isinstance(body,dict) or set(body)-{'job_id','world','round_no','agent','stage'}:
                    raise ValueError('Invalid inspection coordinates.')
                return self.send(200,workflow_service().inspect(**body))
            if self.path == '/api/personas/assignment-preview':
                preview = preview_assignment(body)
                # Retain the browser's bounded workload for the organization.
                if body.get('scenario')=='task_workflow':
                    c=body['config']
                    if preview['slots']>80 or len(c['tasks'])>200: raise ValueError('Workflow preview is too large for the browser.')
                else:
                    validate_config({**body['config'], 'population': None}, web=True)
                return self.send(200, preview)
            if self.path == '/api/personas/import':
                if not isinstance(body, dict) or set(body)-{'text','format','preset','field_map','source'} or not isinstance(body.get('text'), str):
                    raise ValueError('Import expects text, format, preset, optional field_map and source.')
                records = parse_personas(**body)
                return self.send(200, dict(records=records, count=len(records)))
            config = validate_config(body, web=True)
            if self.path == '/api/workforce/preview':
                rows = build_workforce(config, memberships(config))
                meta = workforce_metadata(config, rows)
                meta.pop('workforce')
                return self.send(200, dict(**meta, preview=rows[:20], displayed=min(20,len(rows))))
        except (ValueError, TypeError, KeyError, FileNotFoundError) as error:
            return self.send(400, {'error': str(error)})
        if not RUN_LOCK.acquire(blocking=False):
            return self.send(409, {'error': 'An experiment is already running. Try again after completion.'})
        try:
            self.send(200, run(config))
        except Exception:
            self.send(500, {'error': 'Simulation failed; inspect the local terminal.'})
            raise
        finally:
            RUN_LOCK.release()


def serve(port=8765):
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'ORDO: http://127.0.0.1:{port} (local, rule engines only)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
