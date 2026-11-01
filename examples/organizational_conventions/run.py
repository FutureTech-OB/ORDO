"""Compare seed position and publishing authority inside large organizations.

python -m examples.organizational_conventions.run --preview
python -m examples.organizational_conventions.run --output runs/org-conventions-rules
python -m examples.organizational_conventions.run --engine jev --allow-paid --output runs/org-conventions-jev
"""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
import platform
import time

from orgabm.openrouter import OpenRouterJevEngine
from orgabm.sdk import run_simulation
from .model import OrganizationalConventions,OrganizationEnsemble,rule_engine,STATE


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def expand(raw):
    if not isinstance(raw,dict) or set(raw)-{'base','vary','seeds'}: raise ValueError('Plan accepts base, vary, seeds.')
    base=raw.get('base',{}); vary=raw.get('vary',{}); seeds=raw.get('seeds',[7])
    if not isinstance(base,dict) or not isinstance(vary,dict) or not isinstance(seeds,list) or not seeds or any(type(s) is not int for s in seeds):
        raise ValueError('Invalid plan specification.')
    if any(not isinstance(v,list) or not v for v in vary.values()): raise ValueError('Variation values must be nonempty lists.')
    configs={}
    for values in itertools.product(*vary.values()):
        for seed in seeds:
            configs[f'w{len(configs)}']={**base,**dict(zip(vary,values)), 'seed':seed}
    if not 1<=len(configs)<=48: raise ValueError('Use at most 48 worlds per experiment.')
    if len({c.get('rounds',32) for c in configs.values()})!=1: raise ValueError('A comparison requires equal periods.')
    return configs


def make_worlds(configs): return {wid:OrganizationalConventions(**config) for wid,config in configs.items()}


def export_snapshots(root,worlds,latest):
    root.mkdir(parents=True,exist_ok=False)
    rows=[]
    for wid,w in worlds.items():
        save(root/f'{wid}.json',w.snapshot())
        rows.append(dict(world=wid,config=w.config,environment=w.describe(),completed_periods=w.round,
            last=latest.get(wid),ordinary_encounters=sum(v for a,v in enumerate(w.encounters) if a not in w.seed_ids),
            seed_encounters=sum(w.encounters[a] for a in w.seed_ids)))
    save(root/'worlds.json',rows)
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',default=str(Path(__file__).with_name('large_plan.json')))
    parser.add_argument('--preview',action='store_true')
    parser.add_argument('--engine',choices=['rules','jev'],default='rules')
    parser.add_argument('--allow-paid',action='store_true')
    parser.add_argument('--max-cost-usd',type=float,default=3)
    parser.add_argument('--max-requests',type=int,default=6000)
    parser.add_argument('--output')
    args=parser.parse_args()
    plan=json.loads(Path(args.plan).read_text(encoding='utf-8')); configs=expand(plan)
    sample=make_worlds(configs); periods=next(iter(sample.values())).rounds
    preview=dict(worlds=len(sample),members_per_world=sorted({w.n for w in sample.values()}),periods=periods,
        pairs_per_world_period=sorted({w.pair_budget for w in sample.values()}),
        maximum_jev_decisions=sum(w.pair_budget*2*periods for w in sample.values()),
        tested_factors=['minority position','none / same-audience peer note / delegated official guidance'],
        authority_scope='permission to issue guidance; no forced adoption or extra penalty',
        source_protocol_change='disjoint synchronous pairs within organizational periods')
    batch=OrganizationEnsemble(sample).prepare(1); sizes=[]; items=list(batch.questions.items())
    for i in range(0,len(items),32):
        sizes.append(len(json.dumps(dict(model='typesafe/jev-1.14',state=STATE,questions=dict(items[i:i+32])),ensure_ascii=True).encode()))
    preview['max_first_period_request_bytes']=max(sizes,default=0)
    print(json.dumps(preview,indent=2),flush=True)
    if args.preview:return
    if not args.output:parser.error('--output is required.')
    if args.engine=='jev' and not args.allow_paid:parser.error('--allow-paid is required for Jev.')
    root=Path(args.output); root.mkdir(parents=True,exist_ok=False)
    save(root/'plan-before-calls.json',dict(plan=plan,configs=configs,preview=preview))
    report=dict(status='running',scenario='organizational_conventions',engine_mode=args.engine,
        python=platform.python_version(),groups={},probability_reuse=False,
        source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(__file__).with_name('model.py'),
            Path('orgabm/sdk.py'),Path('orgabm/memory.py'),Path('orgabm/workforce.py'),Path('orgabm/personas.py'),Path('orgabm/openrouter.py')]})
    started=time.perf_counter(); live=None
    try:
        providers=['uniform','history','notice']+(['jev'] if args.engine=='jev' else [])
        for provider in providers:
            worlds=make_worlds(configs)
            def progress(row,provider=provider):
                if provider=='jev':
                    print(json.dumps(dict(engine=provider,**row,cost_usd=live.usage()['recorded_input_cost_usd'])),flush=True)
            env=OrganizationEnsemble(worlds,progress)
            engine=rule_engine(provider) if provider!='jev' else OpenRouterJevEngine(root/'calls',
                cap_usd=args.max_cost_usd,max_requests=args.max_requests,batch_size=32,concurrency=4)
            if provider=='jev':live=engine
            try:
                result=run_simulation(env,engine,rounds=periods,seed=202610,output=root/provider)
                report['groups'][provider]=dict(status=result['status'],decisions=result['decisions'],
                    worlds=export_snapshots(root/f'{provider}-snapshots',worlds,env.latest))
            except Exception:
                report['groups'][provider]=dict(status='failed',
                    worlds=export_snapshots(root/f'{provider}-partial-snapshots',worlds,env.latest))
                raise
            save(root/'verification.json',dict(report,usage=live.usage() if live else {'actual_model_api_calls':0}))
        report['status']='complete'
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__)
        raise
    finally:
        report.update(elapsed_s=time.perf_counter()-started,usage=live.usage() if live else {'actual_model_api_calls':0})
        save(root/'verification.json',report)
    print(json.dumps(dict(status=report['status'],decisions={k:v['decisions'] for k,v in report['groups'].items()},usage=report['usage']),indent=2))


if __name__=='__main__': main()
