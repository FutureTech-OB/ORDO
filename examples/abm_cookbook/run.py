"""Run existing economics, sociology and organization ABMs through ORDO.

python -m examples.abm_cookbook.run --model all --output runs/abm-portability
Default: original rules and exact native-reference comparisons; no API calls.
"""
import argparse
import copy
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import time

from .adapters import ExistingMesaEnvironment, direct_reference, digest
from orgabm.sdk import run_simulation
from orgabm.staged import run_staged_simulation


MODELS={'wealth':'Economics: wealth exchange','cooperation':'Economics and society: spatial cooperation',
        'schelling':'Sociology: residential segregation','organization':'Organization: social learning and knowledge diffusion'}


def cases(model='all'):
    result=[]
    for seed in (7,8,9):
        result.append(dict(model='wealth',config=dict(n=60,width=5,height=5,rounds=15,seed=seed)))
        for threshold in (.3,.6):
            result.append(dict(model='schelling',config=dict(width=12,height=12,density=.75,
                homophily=threshold,rounds=20,seed=seed)))
        for mode in ('Simultaneous','Random','Sequential'):
            for bonus in (1.2,1.8):
                result.append(dict(model='cooperation',config=dict(width=12,height=12,
                    activation_order=mode,defection_bonus=bonus,rounds=20,seed=seed)))
        for contact in ('siloed','bridge'):
            result.append(dict(model='organization',config=dict(agents=120,departments=4,
                contact=contact,rounds=20,seed=seed,engine='best')))
    return [c for c in result if model=='all' or c['model']==model]


def smoke_cases():
    return [dict(model='wealth',config=dict(n=12,width=3,height=3,rounds=2,seed=7)),
            dict(model='schelling',config=dict(width=6,height=6,density=.7,homophily=.4,rounds=2,seed=7)),
            dict(model='cooperation',config=dict(width=6,height=6,activation_order='Simultaneous',
                 defection_bonus=1.6,rounds=3,seed=7)),
            dict(model='organization',config=dict(agents=16,departments=4,contact='bridge',rounds=3,seed=7,engine='best'))]


def save(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def environment(case):
    if case['model']!='organization': return ExistingMesaEnvironment(case['model'],case['config'])
    from orgabm.mesa_bridge import organization_adapter
    class Tracked:
        def __init__(self,config): self.inner=organization_adapter(config); self.trajectory=[]
        def describe(self): return self.inner.describe()
        def prepare(self,t): return self.inner.prepare(t)
        def advance(self,t,actions,probabilities):
            metric=self.inner.advance(t,actions,probabilities)
            world=self.inner.model.world
            self.trajectory.append(dict(round=t,positions=list(world['positions']),balances=list(world['balances'])))
            return metric
    return Tracked(case['config'])


def preview(selected,batch_size=64):
    if not isinstance(selected,list) or not 1<=len(selected)<=100: raise ValueError('Use 1..100 cases.')
    rows=[]
    for case in selected:
        if not isinstance(case,dict) or set(case)!={'model','config'} or case['model'] not in MODELS:
            raise ValueError('Every case needs a registered model name and config.')
        c=case['config']
        if type(c.get('rounds')) is not int or not 1<=c['rounds']<=100: raise ValueError('Use 1..100 rounds.')
        if type(c.get('seed')) is not int or not 0<=c['seed']<2**32: raise ValueError('Invalid seed.')
        if case['model']=='wealth':
            if type(c.get('n')) is not int or not 1<=c['n']<=2000: raise ValueError('Use 1..2,000 wealth agents.')
        if case['model']!='organization':
            if any(type(c.get(k)) is not int or not 3<=c[k]<=50 for k in ('width','height')):
                raise ValueError('Use grids of width and height 3..50.')
            if case['model']=='cooperation':
                if c.get('activation_order') not in ('Simultaneous','Random','Sequential'): raise ValueError('Unknown activation regime.')
                if type(c.get('defection_bonus')) not in (int,float) or not 1<=c['defection_bonus']<=3:
                    raise ValueError('Use a defection bonus in 1..3.')
        e=environment(case)
        n=len(e.inner.model.agents) if case['model']=='organization' else len(e.model.agents)
        sequential=case['model']=='wealth' or case['model']=='cooperation' and c['activation_order']!='Simultaneous'
        rows.append(dict(model=case['model'],agents=n,rounds=c['rounds'],
                         decisions_upper_bound=n*c['rounds'],
                         requests_upper_bound=(n if sequential else math.ceil(n/batch_size))*c['rounds'],
                         activation='sequential-dependent' if sequential else 'batched-round',
                         config=c))
    return dict(worlds=len(rows),decisions_upper_bound=sum(r['decisions_upper_bound'] for r in rows),
                requests_upper_bound=sum(r['requests_upper_bound'] for r in rows),cases=rows)


def run_case(case,folder,engine_kind,*,batch_size=64,concurrency=4,cap_usd=.1):
    folder.mkdir()
    save(folder/'case.json',case)
    env=environment(case); kind=case['model']; config=case['config']
    if engine_kind=='native':
        if kind=='organization':
            from orgabm.mesa_bridge import organization_rule
            engine=organization_rule(config.get('engine','best'))
        else: engine=env.native_engine()
    else:
        from orgabm.engines import JevEngine
        engine=JevEngine(folder,cap_usd,batch_size,concurrency)
    run=run_simulation if kind=='organization' else run_staged_simulation
    result=run(env,engine,rounds=config['rounds'],seed=config['seed'],output=folder/'ordo')
    if kind=='organization':
        from orgabm.experiment import run as reference_run
        native=folder/'reference'; native.mkdir()
        reference=reference_run(config,output=native)
        states=[json.loads(line) for line in (native/'trajectory.jsonl').read_text(encoding='utf-8').splitlines()]
        equal=(result['metrics']==reference['metrics'] and
               env.describe()['initial_state_sha256']==reference['initial_state_sha256'] and
               all(a['positions']==b['positions_after'] for a,b in zip(env.trajectory,states)) and
               env.trajectory[-1]['balances']==reference['final_balances'])
        scope='Existing independent Python reference for the published-model adaptation; not original R replication.'
    else:
        reference=direct_reference(kind,config)
        save(folder/'native-reference.json',reference)
        equal=env.initial==reference['initial'] and env.trajectory==reference['states'] and result['metrics']==reference['metrics']
        scope='Unmodified installed Mesa 3.5.1 example; full agent, clock and RNG states per round.'
    with (folder/'ordo-states.jsonl').open('w',encoding='utf-8') as stream:
        for row in env.trajectory: stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
    audit=dict(engine=engine_kind,reference_scope=scope,completed_rounds=result['completed_rounds'],
               reference_comparison_applicable=engine_kind=='native',
               exact_reference_match=equal if engine_kind=='native' else None,
               changed_engine_matches_reference=equal if engine_kind!='native' else None,
               ordo_trajectory_sha256=digest(env.trajectory))
    save(folder/'audit.json',audit)
    if engine_kind=='native' and not equal: raise AssertionError('ORDO changed the native baseline; inspect audit evidence.')
    return dict(model=kind,engine=engine_kind,seed=config['seed'],config=config,
                decisions=result['decisions'],elapsed_s=result['elapsed_s'],usage=result['usage'],
                exact_reference_match=audit['exact_reference_match'],reference_scope=scope,
                completed_rounds=result['completed_rounds'],final=result['metrics'][-1],evidence=folder.name)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',choices=['all',*MODELS],default='all')
    parser.add_argument('--cases',type=Path,help='An exported editable cases.json or jev_smoke_cases.json.')
    parser.add_argument('--engine',choices=['native','jev'],default='native')
    parser.add_argument('--preview',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--batch-size',type=int,default=64)
    parser.add_argument('--concurrency',type=int,default=4)
    parser.add_argument('--max-requests',type=int,default=0)
    parser.add_argument('--max-cost-usd',type=float,default=.1)
    args=parser.parse_args()
    if not 1<=args.batch_size<=128 or not 1<=args.concurrency<=16: parser.error('Invalid batching limits.')
    if not math.isfinite(args.max_cost_usd) or args.max_cost_usd<=0: parser.error('Use a positive spending cap.')
    selected=json.loads(args.cases.read_text(encoding='utf-8')) if args.cases else cases(args.model)
    details=preview(selected,args.batch_size)
    if args.preview:
        print(json.dumps(dict(engine=args.engine,**details),ensure_ascii=False,indent=2)); return
    if args.output is None: parser.error('Choose a new output directory.')
    if args.engine=='jev':
        if args.max_requests<details['requests_upper_bound']: parser.error('Set --max-requests to the preview upper bound or higher.')
        if not os.environ.get('TYPESAFE_API_KEY'): parser.error('Set TYPESAFE_API_KEY for live decisions; no API calls submitted.')
    args.output.mkdir(parents=True,exist_ok=False)
    save(args.output/'cases.json',selected); save(args.output/'preview.json',details)
    save(args.output/'jev_smoke_cases.json',smoke_cases())
    manifest=dict(status='running',engine=args.engine,python=platform.python_version(),
        worlds=len(selected),completed_worlds=0,source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                                           for p in Path(__file__).parent.glob('*.py')},
        paid_api_calls=0,recorded_cost_usd=0,rows=[])
    save(args.output/'manifest.json',manifest)
    started=time.perf_counter()
    try:
        for i,case in enumerate(selected):
            row=run_case(case,args.output/f'world-{i:03d}',args.engine,batch_size=args.batch_size,
                         concurrency=args.concurrency,cap_usd=args.max_cost_usd-manifest['recorded_cost_usd'])
            manifest['rows'].append(row); manifest['completed_worlds']+=1
            manifest['paid_api_calls']+=row['usage'].get('successful_requests',0)
            manifest['recorded_cost_usd']+=row['usage'].get('recorded_input_cost_usd',0)
            save(args.output/'manifest.json',manifest)
            print(f'{i+1}/{len(selected)} {case["model"]}: {row["completed_rounds"]} rounds, {row["decisions"]} decisions, exact={row["exact_reference_match"]}',flush=True)
        manifest['status']='complete'
    except Exception as error:
        manifest.update(status='failed',error_type=type(error).__name__)
        raise
    finally:
        # Include recorded provider usage from failed/partial worlds as well.
        recorded=[json.loads(p.read_text(encoding='utf-8')).get('usage',{})
                  for p in args.output.glob('world-*/ordo/result.json')]
        manifest['paid_api_calls']=sum(u.get('successful_requests',0) for u in recorded)
        manifest['recorded_cost_usd']=sum(u.get('recorded_input_cost_usd',0) for u in recorded)
        manifest['accounting']='Recorded successful provider usage, including partial worlds; ambiguous failed requests may incur additional charges.'
        manifest['elapsed_s']=time.perf_counter()-started
        save(args.output/'manifest.json',manifest)
        save(args.output/'summary.json',manifest['rows'])
        with (args.output/'summary.csv').open('w',encoding='utf-8-sig',newline='') as stream:
            fields=['model','engine','seed','completed_rounds','decisions','elapsed_s','exact_reference_match','config','final','evidence']
            writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore'); writer.writeheader()
            writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,dict) else v for k,v in r.items()} for r in manifest['rows'])


if __name__=='__main__': main()
