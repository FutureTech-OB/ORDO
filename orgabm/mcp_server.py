"""Local stdio tools for DeepSeek Harness and other MCP-compatible research assistants."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from .plans import expand_plan
from .placement import preview_assignment, assign_personas, save_assignment


class ExperimentService:
    def __init__(self, root, *, allow_paid=False, max_requests=0, max_cost_usd=0.1):
        if type(max_requests) is not int or max_requests < 0 or type(max_cost_usd) not in (int,float) or not math.isfinite(max_cost_usd) or max_cost_usd <= 0:
            raise ValueError('Invalid server request or cost limit.')
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.allow_paid, self.remaining_requests = allow_paid, max_requests
        self.remaining_cost_usd = max_cost_usd
        self.lock = threading.RLock()
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.jobs = {}

    def describe(self):
        return dict(schema_version='0.6.0', scenarios=['nk_organization','task_workflow'],
                    workflow=dict(config='base.tasks: explicit DAG tasks with id, owner, dependencies, effort, cost, value, signal, success_probability and deadline. Optional revision_effort. Reuse population and structure; workflow role actions differ from NK.',
                        organization='delegation_limit, authority_level (direct/top), review_capacity (1..8), worker_capacity, budget, individual_reward_weight, max_revisions. See examples/workflow_plan.json.',
                        memory='Optional base.memory: organization/department/personal trees, tree readers and inherited node grants, summary/detail levels and round windows. Permissions filter every local question before inference; researcher-only visibility audit is in stage effects. See examples/templates/plans/memory_permissions.json.',
                        execution='Employee proposal -> sequential manager review slots -> work. Fresh Jev batches within each stage. FIFO dossiers; managers do not see other Personas or true success probabilities. Stage failures preserve earlier stage commits and stop the run.',
                        counts='Workflow preview decision/request counts are upper bounds. final contains cumulative outcomes; execution_events is the final tick only.',
                        rules=['threshold','permissive']),
                    persona=dict(population='base.population: records, sampling (ordered/without_replacement/with_replacement), optional seed and weights.',
                        fields=['id','name','description','background','traits','skills','goals','source'],
                        structure='base.structure: template (flat/department_hierarchy/custom), roles, optional explicit assignments.',
                        import_formats='Use orgabm.personas.load_personas for CSV/JSON/JSONL or import_personas for dataset rows. Presets: custom/nemotron/personahub/finepersonas. Plans contain normalized records, not paths.',
                        assignment='preview_persona_assignment / start_persona_assignment: job contains config with population.records pool, mode pool or stream, threshold default 0.5, seed, batch_size, optional max_evaluations and context. Stream randomly samples candidates and accepts P(holds target position) >= threshold. Pool scores all pairs and assigns by probability weight. No duplicates. Use get_experiment for status; completed config_file is a local artifact. Costs use the same process-wide Jev limits, separate from ABM decisions.',
                        limitations='Rules ignore Persona descriptions. Role permissions constrain choices. NK managers do not make approval decisions.'),
                    roles={'assistant':'Plan and orchestrate experiments; report measured evidence only.',
                           'simulation':'Mesa/ABM computes transitions and outcomes.',
                           'decisions':'Jev native batches or explicit rules; no chat-model simulation in the plan service.'},
                    tools=['describe_interface','preview_experiment','start_experiment','get_experiment','inspect_decision','preview_persona_assignment','start_persona_assignment'],
                    example=dict(scenario='nk_organization',base={'agents':16,'rounds':3,'departments':4},
                                 vary={'contact':['siloed','bridge']},seeds=[7,8],decision={'provider':'rule','rule':'best'}),
                    local_paid_execution_enabled=self.allow_paid,remaining_provider_requests=self.remaining_requests,
                    remaining_cost_guard_usd=self.remaining_cost_usd,
                    custom_models='Implement Environment or MesaAdapter through the Python SDK.',
                    credentials='Configured in process environment; never put keys in tool arguments.',
                    note='The planning assistant and simulated decision engine are independently configured and billed. Zero simulation provider_requests excludes Harness model calls. In results, final contains last-round metrics except cumulative_net; whole-run counts are provided separately. Do not infer all-round behavior from final-round counts. Use get_experiment with wait_seconds to avoid repeated model-driven polling.')

    def start_assignment(self, job):
        preview = preview_assignment(job)
        with self.lock:
            if any(not f.done() for f in self.jobs.values()):
                raise ValueError('One job is already running. Inspect it before starting another.')
            count = preview['max_provider_requests']
            if not self.allow_paid or count > self.remaining_requests:
                raise ValueError('Paid execution is disabled or exceeds the server request allowance.')
            if not os.environ.get('TYPESAFE_API_KEY'):
                raise ValueError('Set TYPESAFE_API_KEY in the server environment for Jev.')
            if self.remaining_cost_usd <= 0:
                raise ValueError('Server cost guard exhausted.')
            job = json.loads(json.dumps(job, allow_nan=False))
            self.remaining_requests -= count
            job_id = uuid.uuid4().hex
            directory = self.root/job_id
            directory.mkdir()
            (directory/'job.json').write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding='utf-8')
            self._write_status(directory, dict(id=job_id, kind='persona_assignment', status='queued', preview=preview))
            self.jobs[job_id] = self.pool.submit(self._execute_assignment, job_id, job, preview)
        return dict(id=job_id, kind='persona_assignment', status='queued', preview=preview)

    def _execute_assignment(self, job_id, job, preview):
        from .engines import JevEngine
        directory = self.root/job_id
        status = dict(id=job_id, kind='persona_assignment', status='running', preview=preview)
        self._write_status(directory, status)
        try:
            engine = JevEngine(directory, self.remaining_cost_usd, preview['batch_size'], concurrency=1)
            result = assign_personas(job, engine, output=directory)
            save_assignment(result, directory)
            with self.lock:
                self.remaining_cost_usd = max(0, self.remaining_cost_usd - engine.cost)
                self.remaining_requests += preview['max_provider_requests'] - engine.requests
            status.update({k: result[k] for k in ['status','assigned','evaluated_pairs','missing_by_role','usage','stop_reason']})
            status.update(evidence_file=str(directory/'assignment.json'),
                          config_file=str(directory/'config.json') if result['config'] else None,
                          note='Population preparation only. No ABM rounds executed; scores are not calibrated human frequencies.')
        except Exception as error:
            with self.lock:
                self.remaining_cost_usd = 0  # Ambiguous paid failure: no automatic retry.
            status.update(status='failed', error_type=type(error).__name__,
                          message='Assignment stopped; inspect local evidence. No automatic retry or threshold relaxation.')
        self._write_status(directory, status)

    def start(self, plan):
        expanded = expand_plan(plan)
        with self.lock:
            if any(not f.done() for f in self.jobs.values()):
                raise ValueError('One experiment is already running. Inspect it before starting another.')
            count = expanded['provider_requests']
            if count and (not self.allow_paid or count>self.remaining_requests):
                raise ValueError('Paid execution is disabled or exceeds the server request allowance.')
            if count:
                if not os.environ.get('TYPESAFE_API_KEY'):
                    raise ValueError('Set TYPESAFE_API_KEY in the server environment for Jev.')
                if self.remaining_cost_usd <= 0:
                    raise ValueError('Server cost guard exhausted.')
            self.remaining_requests -= count
            job_id = uuid.uuid4().hex
            directory = self.root/job_id
            directory.mkdir()
            (directory/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
            self._write_status(directory,{'id':job_id,'status':'queued','completed_worlds':0,
                                          'worlds':expanded['worlds'],'results':[]})
            self.jobs[job_id] = self.pool.submit(self._execute,job_id,expanded)
        return {'id':job_id,'status':'queued','worlds':expanded['worlds'],'decisions':expanded['decisions'],
                'counts_are_upper_bounds':expanded.get('counts_are_upper_bounds',False)}

    def _write_status(self,directory,value):
        with self.lock:
            temp=directory/'status.tmp'
            temp.write_text(json.dumps(value,indent=2),encoding='utf-8')
            temp.replace(directory/'status.json')

    def _execute(self,job_id,expanded):
        directory=self.root/job_id
        status={'id':job_id,'status':'running','completed_worlds':0,'worlds':expanded['worlds'],'results':[]}
        try:
            self._write_status(directory,status)
            from .mesa_bridge import organization_adapter, organization_rule
            from .sdk import run_simulation
            workflow = expanded['scenario']=='task_workflow'
            if workflow:
                from .workflow_mesa import WorkflowModel, workflow_rule
                from .staged import run_staged_simulation
            for i,c in enumerate(expanded['configs']):
                d=expanded['decision']
                paid=d.get('provider','rule')=='jev'
                if paid:
                    from .engines import JevEngine
                    call_dir=directory/f'calls-{i}'
                    call_dir.mkdir()
                    engine=JevEngine(output=call_dir,cap_usd=self.remaining_cost_usd,
                                     batch_size=d.get('batch_size',64),concurrency=d.get('concurrency',4))
                else:
                    engine=workflow_rule(d['rule']) if workflow else organization_rule(d.get('rule','best'))
                try:
                    environment = WorkflowModel(c) if workflow else organization_adapter(c)
                    runner = run_staged_simulation if workflow else run_simulation
                    r=runner(environment,engine,rounds=c['rounds'],seed=c['seed'],output=directory/f'world-{i}')
                except Exception:
                    if paid:
                        # Ambiguous failed requests may be billed. Stop further paid work in this process.
                        with self.lock:self.remaining_cost_usd=0
                    raise
                if paid:
                    with self.lock:self.remaining_cost_usd=max(0,self.remaining_cost_usd-engine.cost)
                if workflow:
                    snapshot=environment.snapshot()
                    (directory/f'world-{i}'/'workflow-state.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf-8')
                    status['results'].append(dict(world=i,config=c,final=r['metrics'][-1],
                        population_sha256=r['environment']['population_sha256'],organization_sha256=r['environment']['organization_sha256'],
                        decisions=r['decisions'],metric_scope='Final counts and cumulative fields cover all completed ticks; execution_events covers only the final tick.',
                        usage=r['usage'],elapsed_s=r['elapsed_s'],state_file=str(directory/f'world-{i}'/'workflow-state.json')))
                else:
                    status['results'].append(dict(world=i,config=c,final=r['metrics'][-1],
                    population_sha256=r['environment']['population_sha256'],
                    organization_sha256=r['environment']['organization_sha256'],
                    whole_run=dict(mean_exploration=sum(m['explore_share'] for m in r['metrics'])/len(r['metrics']),
                        successful_searches=sum(m['successful_searches'] for m in r['metrics']),
                        failed_searches=sum(m['failed_searches'] for m in r['metrics']),
                        cross_department_adoptions=sum(m['cross_department_adoptions'] for m in r['metrics'])),
                    metric_scope='final is the last round; cumulative_net is accumulated per-agent earnings; whole_run sums counts over all rounds.',
                        usage=r['usage'],elapsed_s=r['elapsed_s']))
                status['completed_worlds']=i+1
                self._write_status(directory,status)
            status['status']='complete'
        except Exception as error:
            status.update(status='failed',error_type=type(error).__name__,
                          message='Execution stopped; inspect the local run logs. No automatic retry.')
        self._write_status(directory,status)

    def _directory(self,job_id):
        if not re.fullmatch('[0-9a-f]{32}',job_id):
            raise ValueError('Invalid experiment ID.')
        return self.root/job_id

    def get(self,job_id,wait_seconds=0):
        self._directory(job_id)
        if type(wait_seconds) is not int or not 0<=wait_seconds<=15:
            raise ValueError('wait_seconds must be an integer from 0 to 15.')
        future=self.jobs.get(job_id)
        if future and wait_seconds:
            try:future.result(timeout=wait_seconds)
            except FutureTimeout:pass
            except Exception:pass  # Expose worker failure through the persisted status below.
        with self.lock:
            result=json.loads((self._directory(job_id)/'status.json').read_text(encoding='utf-8'))
            future=self.jobs.get(job_id)
            if future and future.done() and future.exception() is not None:
                result.update(status='failed',error_type=type(future.exception()).__name__,
                              message='The worker could not persist its result.')
            return result

    def inspect(self,job_id,world,round_no,agent,stage=None):
        if any(type(x) is not int or x<0 for x in [world,agent]) or type(round_no) is not int or round_no<1:
            raise ValueError('Invalid decision coordinates.')
        path=self._directory(job_id)/f'world-{world}'/'events.jsonl'
        matches=[]
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                event=json.loads(line)
                if event['round']==round_no and (stage is None or event.get('stage')==stage):
                    qid=next((q for q,a in event.get('agent_ids',{}).items() if a==agent),None)
                    if qid is None: continue
                    matches.append(dict(id=qid,stage=event.get('stage'),question=event['questions'][qid],probabilities=event['probabilities'][qid],
                                proposed_action=event['actions'][qid],round_metrics=event.get('metrics'),stage_effects=event.get('effects')))
        if len(matches)==1: return matches[0]
        if len(matches)>1: raise ValueError('This member decided in several stages; provide stage (proposal or review_N).')
        raise ValueError('Decision not found in completed event records.')


def create_server(service):
    from mcp.server.fastmcp import FastMCP
    from pydantic import BaseModel, ConfigDict, Field
    from typing import Literal

    class DecisionSpec(BaseModel):
        model_config=ConfigDict(extra='forbid')
        provider: Literal['rule','jev']='rule'
        rule: Literal['best','conformity','threshold','permissive']='best'
        batch_size: int=Field(default=64,ge=1,le=128)
        concurrency: int=Field(default=4,ge=1,le=16)

    class ToolPlan(BaseModel):
        model_config=ConfigDict(extra='forbid')
        scenario: Literal['nk_organization','task_workflow']='nk_organization'
        base: dict=Field(default_factory=dict,description='Fixed scenario parameters. NK: agents, departments, rounds, contact, guidance, penalty, anonymous, approval_gain, intervention_round, population, structure. task_workflow: agents, departments, rounds, tasks, population, structure, memory, delegation_limit, authority_level, review_capacity, worker_capacity, budget, individual_reward_weight, max_revisions, objective. Put seed and engine in seeds/decision.')
        vary: dict[str,list]=Field(default_factory=dict,description='Factor grid: parameter name to list of values, e.g. {"contact":["siloed","bridge"]}.')
        seeds: list[int]=Field(default_factory=lambda:[42],description='Distinct random seeds, reused across all factor combinations.')
        decision: DecisionSpec=Field(default_factory=DecisionSpec)

    server=FastMCP('ORDO',instructions='You are a research assistant, not a simulated agent or source of experimental outcomes. Read describe_interface before planning. Preview and validate the complete experiment plan before starting it. Use measured tool results for conclusions; distinguish final-round and whole-run metrics.')

    @server.tool()
    def describe_interface() -> dict:
        """Read available scenarios, experiment-plan example and server limits."""
        return service.describe()

    @server.tool()
    def preview_experiment(plan: ToolPlan) -> dict:
        """Validate a factor grid and paired seeds; return workload without API calls."""
        return expand_plan(plan.model_dump(exclude_unset=True))

    @server.tool()
    def start_experiment(plan: ToolPlan) -> dict:
        """Start a local experiment and return its ID. Paid runs require server-side opt-in and allowance."""
        return service.start(plan.model_dump(exclude_unset=True))

    @server.tool()
    def get_experiment(experiment_id: str, wait_seconds: int=10) -> dict:
        """Wait up to 0–15 seconds and read results, avoiding rapid polling. Simulation usage excludes the assistant's API calls."""
        return service.get(experiment_id,wait_seconds=wait_seconds)

    @server.tool()
    def inspect_decision(experiment_id: str, world: int, round_no: int, agent: int, stage: str | None=None) -> dict:
        """Read one agent's local question, probability vector and proposed action."""
        return service.inspect(experiment_id,world,round_no,agent,stage)

    @server.tool()
    def preview_persona_assignment(job: dict) -> dict:
        """Preview role quotas and maximum calls. No calls. Job: config with population.records, mode pool/stream, threshold (stream, default 0.5), seed, batch_size, max_evaluations, context."""
        return preview_assignment(job)

    @server.tool()
    def start_persona_assignment(job: dict) -> dict:
        """Start paid Jev population construction with the previewed job. Uses server allowances. Poll get_experiment; read config_file only when complete. This does not run the ABM."""
        return service.start_assignment(job)

    return server


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output-root',default='runs/harness')
    parser.add_argument('--allow-paid',action='store_true')
    parser.add_argument('--max-requests',type=int,default=0)
    parser.add_argument('--max-cost-usd',type=float,default=0.1)
    args=parser.parse_args()
    if args.max_requests<0 or (args.allow_paid and args.max_requests<1) or not math.isfinite(args.max_cost_usd) or args.max_cost_usd<=0:
        parser.error('Paid execution requires a positive process-wide request allowance.')
    create_server(ExperimentService(args.output_root,allow_paid=args.allow_paid,max_requests=args.max_requests,max_cost_usd=args.max_cost_usd)).run(transport='stdio')


if __name__=='__main__':main()
