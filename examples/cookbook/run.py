"""Run or export the ORDO cookbook. Execution is offline; no model API calls.

python -m examples.cookbook.run --recipe all --output runs/cookbook-local
"""
import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
import platform
import statistics
import time
from .recipes import RECIPES, ROOT, cases, assignment_job, occupancy_fixture, information_rule, live_plan


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def execute_plan(plan, engine_kind, output, case_name):
    from orgabm.plans import expand_plan
    from orgabm.sdk import run_simulation
    from orgabm.staged import run_staged_simulation
    from orgabm.mesa_bridge import organization_adapter, organization_rule
    from orgabm.workflow_mesa import WorkflowModel, workflow_rule
    from orgabm.memory import MemoryForest
    expanded = expand_plan(plan)
    if expanded['decision'].get('provider') != 'rule':
        raise ValueError('Cookbook verification only executes offline engines.')
    rows = []
    for i, config in enumerate(expanded['configs']):
        started = time.perf_counter()
        workflow = expanded['scenario'] == 'task_workflow'
        environment = WorkflowModel(config) if workflow else organization_adapter(config)
        if engine_kind == 'information_rule': engine = information_rule()
        elif engine_kind == 'memory_blind_control': engine = workflow_rule('permissive')
        else: engine = workflow_rule(expanded['decision']['rule']) if workflow else organization_rule(expanded['decision']['rule'])
        runner = run_staged_simulation if workflow else run_simulation
        destination = output/f'world-{i:03d}'
        result = runner(environment, engine, rounds=config['rounds'], seed=config['seed'], output=destination)
        save(destination/'config.json', config)
        if workflow: save(destination/'workflow-state.json', environment.snapshot())
        if workflow and config.get('memory'):
            forest = MemoryForest(config['memory'], environment.roster)
            views = [dict(round=t, agent=a, view=forest.observe(a, t)[0]) for t in (1,3) for a in (0,1,4,5)]
            save(destination/'visibility-examples.json', views)
        final = result['metrics'][-1]
        row = dict(case=case_name, world=i, seed=config['seed'], agents=config['agents'], rounds=config['rounds'],
                   engine=getattr(engine,'name',type(engine).__name__), decisions=result['decisions'],
                   elapsed_s=time.perf_counter()-started, provider_requests=0,
                   population_sha256=result['environment']['population_sha256'],
                   evidence=str(destination.relative_to(output.parent)))
        row.update({k:config[k] for k in ('contact','approval_gain','delegation_limit','review_capacity') if k in config})
        for key in ('completed_tasks','successful_tasks','blocked_tasks','queue_length','missed_deadlines',
                    'net_value','gross_performance','cumulative_net','unique_solutions','department_gap'):
            if key in final: row[key] = final[key]
        if workflow:
            row.update({key:final['cumulative'][key] for key in ('requests','reviews','approvals','queue_wait_ticks','budget_denials')})
        else:
            row.update({f'total_{key}':sum(m[key] for m in result['metrics']) for key in ('cross_department_adoptions','approval_denials')})
        row['event_log_bytes'] = (destination/'events.jsonl').stat().st_size
        rows.append(row)
    return rows


def record_summary(output, recipe, rows):
    save(output/'summary.json',rows)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with (output/'summary.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields); writer.writeheader()
        writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v
                         for k,v in row.items()} for row in rows)
    metrics = {'01':['gross_performance','cumulative_net','total_cross_department_adoptions','total_approval_denials'],
               '02':['completed_tasks','net_value','queue_wait_ticks','requests'],
               '03':['completed_tasks','net_value','queue_wait_ticks','requests'],
               '04':['assigned','evaluated_pairs'],
               '05':['completed_tasks','net_value','decisions','elapsed_s','event_log_bytes']}.get(recipe,[])
    grouping = ['case'] + (['contact','approval_gain'] if recipe=='01' else ['delegation_limit','review_capacity'] if recipe=='02' else ['status'] if recipe=='04' else [])
    groups = {}
    for row in rows: groups.setdefault(tuple(row[k] for k in grouping),[]).append(row)
    aggregate = [{**dict(zip(grouping,key)), 'worlds':len(values),
                  **{m:statistics.mean(v[m] for v in values) for m in metrics}} for key,values in groups.items()]
    save(output/'condition-means.json',aggregate)
    contrasts = []
    if recipe in ('01','02'):
        first,second,low,high = ('contact','approval_gain','siloed','bridge') if recipe=='01' else ('delegation_limit','review_capacity',0,2)
        for seed in sorted({r['seed'] for r in rows}):
            effects = {}
            for level in sorted({r[second] for r in rows}):
                a=next(r for r in rows if r['seed']==seed and r[first]==low and r[second]==level)
                b=next(r for r in rows if r['seed']==seed and r[first]==high and r[second]==level)
                effects[level]={m:b[m]-a[m] for m in metrics}
                contrasts.append(dict(seed=seed,contrast=f'{first}: {high} minus {low}',at={second:level},difference=effects[level]))
            levels=sorted(effects)
            contrasts.append(dict(seed=seed,contrast=f'interaction: effect at {second}={levels[-1]} minus effect at {levels[0]}',
                                  difference={m:effects[levels[-1]][m]-effects[levels[0]][m] for m in metrics}))
    elif recipe=='03':
        for seed in sorted({r['seed'] for r in rows}):
            for engine in ('information_rule','memory_blind_control'):
                a=next(r for r in rows if r['seed']==seed and r['case']==f'manager_only__{engine}')
                for policy in ('shared_now','shared_round_3'):
                    b=next(r for r in rows if r['seed']==seed and r['case']==f'{policy}__{engine}')
                    contrasts.append(dict(seed=seed,contrast=f'{policy} minus manager_only',engine=engine,
                                          difference={m:b[m]-a[m] for m in metrics}))
    save(output/'paired-contrasts.json',contrasts)
    lines=[f'# {RECIPES[recipe]}: recorded offline results','',
           'Results use explicit rules or synthetic scores. Independent worlds are the comparison units.','',
           'World records: summary.json; paired contrasts: paired-contrasts.json; complete events: individual world directories.','']
    if metrics:
        headers=grouping+['worlds']+metrics
        lines+=['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']
        for row in aggregate:
            lines.append('| '+' | '.join(f'{row[h]:.3f}' if isinstance(row[h],float) else str(row[h]) for h in headers)+' |')
    (output/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def run_assignment(output,export_only):
    from orgabm.placement import assign_personas,save_assignment,preview_assignment
    rows=[]
    for name,mode,threshold in [('pool','pool',.5),('stream','stream',.5),('unfilled','stream',.95)]:
        folder=output/name; folder.mkdir()
        job=assignment_job(mode,threshold)
        save(folder/'job.json',job); save(folder/'preview.json',preview_assignment(job))
        if export_only: continue
        result=assign_personas(job,occupancy_fixture(),output=folder)
        save_assignment(result,folder)
        row=dict(case=name,status=result['status'],assigned=result['assigned'],evaluated_pairs=result['evaluated_pairs'],
                 missing_by_role=result['missing_by_role'],provider_requests=0,score_source='synthetic fixture, not Jev')
        if result['config']:
            base=copy.deepcopy(result['config'])
            for key in ('seed','engine','batch_size','concurrency'): base.pop(key,None)
            plan=dict(scenario='task_workflow',base=base,vary={'delegation_limit':[0,2]},seeds=[7],decision={'provider':'rule','rule':'threshold'})
            save(folder/'frozen-population-plan.json',plan)
            followup=execute_plan(plan,'registered',folder,'fixed_population')
            if len({r['population_sha256'] for r in followup})!=1: raise AssertionError('Population changed between institutions.')
            row['downstream_worlds']=followup
        rows.append(row)
    if not export_only: record_summary(output,'04',rows)
    return rows


def run_recipe(recipe,output,*,scale_agents=1000,export_only=False):
    output.mkdir(parents=True,exist_ok=False)
    if recipe=='04': return run_assignment(output,export_only)
    rows,manifest=[],[]
    from orgabm.plans import expand_plan
    for name,plan,kind in cases(recipe,scale_agents):
        folder=output/name; folder.mkdir()
        if kind=='memory_blind_control': plan['decision']['rule']='permissive'
        preview=expand_plan(plan)
        save(folder/'case.json',dict(plan=plan,offline_engine=kind,recipe=recipe))
        # Custom SDK rules are never mislabelled as executable registered plans.
        if kind!='information_rule': save(folder/'plan.json',plan)
        if kind!='memory_blind_control':
            live=live_plan(plan); save(folder/'jev-plan.json',live)
            save(folder/'jev-preview.json',{k:v for k,v in expand_plan(live).items() if k!='configs'})
        manifest.append(dict(case=name,offline_engine=kind,worlds=preview['worlds'],decisions_upper_bound=preview['decisions'],
                             requires_sdk=kind=='information_rule',live_executed=False))
        if not export_only: rows.extend(execute_plan(plan,kind,folder,name))
    save(output/'manifest.json',manifest)
    if not export_only: record_summary(output,recipe,rows)
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe',choices=['all',*RECIPES],default='all')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--export-only',action='store_true',help='Only write plans and previews; never call an API.')
    parser.add_argument('--scale-agents',type=int,default=1000)
    args=parser.parse_args()
    if not 100<=args.scale_agents<=10000 or args.scale_agents%10: parser.error('Use 100..10,000 scale members in groups of ten.')
    selected=list(RECIPES) if args.recipe=='all' else [args.recipe]
    args.output.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    manifest=dict(status='running',offline=True,live_api_calls=0,python=platform.python_version(),recipes=[],
                  source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in [*Path(__file__).parent.glob('*.py'),*(ROOT/'orgabm').glob('*.py')]})
    save(args.output/'cookbook-run.json',manifest)
    try:
        for recipe in selected:
            rows=run_recipe(recipe,args.output/recipe,scale_agents=args.scale_agents,export_only=args.export_only)
            manifest['recipes'].append(dict(id=recipe,title=RECIPES[recipe],rows=len(rows)))
            save(args.output/'cookbook-run.json',manifest)
            print(f'{recipe}: {RECIPES[recipe]} — {len(rows)} result rows',flush=True)
        manifest['status']='exported' if args.export_only else 'complete'
    except Exception as error:
        manifest.update(status='failed',error_type=type(error).__name__)
        raise
    finally:
        manifest['elapsed_s']=time.perf_counter()-started
        save(args.output/'cookbook-run.json',manifest)


if __name__=='__main__': main()
