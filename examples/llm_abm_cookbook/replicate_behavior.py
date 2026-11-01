"""Predeclared first behavioral replication using fresh Jev probabilities.

python -m examples.llm_abm_cookbook.replicate_behavior --allow-paid --output runs/behavior
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import platform
import time

from orgabm.openrouter import OpenRouterJevEngine
from orgabm.sdk import FunctionEngine,run_simulation
from .behavior import make_naming_worlds,make_opinion_worlds


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-paid',action='store_true')
    parser.add_argument('--output',required=True)
    parser.add_argument('--max-cost-usd',type=float,default=2)
    parser.add_argument('--max-requests',type=int,default=6000)
    parser.add_argument('--only',choices=['all','naming','opinion'],default='all')
    args=parser.parse_args()
    if not args.allow_paid: parser.error('Explicit --allow-paid is required.')
    root=Path(args.output); root.mkdir(parents=True,exist_ok=False)
    engine=OpenRouterJevEngine(root/'calls',cap_usd=args.max_cost_usd,max_requests=args.max_requests,
                               batch_size=16,concurrency=4)
    factories={'naming':make_naming_worlds,'opinion':make_opinion_worlds}
    if args.only!='all': factories={args.only:factories[args.only]}
    report=dict(status='running',evidence='fresh_behavioral_replication_attempt_with_Jev_substitution',
        python=platform.python_version(),probability_reuse=False,groups={},
        protocol_limits=['model changed from paper to Jev','typed output, no original chain of thought or LLM temperature',
            'semantic prompt adaptation','fewer independent repetitions than the full papers',
            'minority first-stage Q to M only; no reverse-direction critical-mass claim',
            'no group-fragmentation or complete critical-size curve in this first stage'],
        source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
            Path('orgabm/sdk.py'),Path('orgabm/openrouter.py'),Path(__file__),Path(__file__).with_name('behavior.py'),
            Path(__file__).with_name('environments.py')]})
    plan={group:dict(configurations=(w:=factory()).configurations,max_updates=w.max_updates,
        stop_rules='spontaneous: 72 most recent matches and >=95% one name; opinion: unanimity or t=10; minority: fixed 1000 pairs, report first 95% target window and final window')
        for group,factory in factories.items()}
    save(root/'plan-before-calls.json',plan)
    started=time.perf_counter()
    try:
        for group,factory in factories.items():
            world=factory()
            def progress(row,group=group):
                print(json.dumps(dict(group=group,engine='jev',**row,usage=engine.usage())),flush=True)
            world.progress=progress
            result=run_simulation(world,engine,rounds=max(world.max_updates.values()),seed=717,
                                   output=root/f'{group}-jev')
            paid=dict(status=result['status'],decisions=result['decisions'],worlds=world.summaries())
            save(root/f'{group}-jev-worlds.json',paid)
            report['groups'][group]={'jev':paid}; save(root/'verification.json',dict(report,usage=engine.usage()))
            control=factory()
            free=run_simulation(control,FunctionEngine(lambda s,q:{k:1/len(q['criteria']) for k in q['criteria']},
                name='uniform-random-explicit-rule'),rounds=max(control.max_updates.values()),seed=717,
                output=root/f'{group}-uniform')
            report['groups'][group]['uniform']=dict(status=free['status'],decisions=free['decisions'],worlds=control.summaries())
            save(root/f'{group}-uniform-worlds.json',report['groups'][group]['uniform'])
            save(root/'verification.json',dict(report,usage=engine.usage()))
        report['status']='complete'
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__)
        raise
    finally:
        report.update(usage=engine.usage(),elapsed_s=time.perf_counter()-started)
        save(root/'verification.json',report)
    print(json.dumps(dict(status=report['status'],usage=engine.usage(),elapsed_s=report['elapsed_s']),indent=2))


if __name__=='__main__': main()
