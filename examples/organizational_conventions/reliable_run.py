"""Recommended new-run entry point with explicit bounded retry settings.

The original run.py remains the frozen strict-mode driver for earlier evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import time

from orgabm.openrouter_reliable import ReliableOpenRouterJevEngine
from orgabm.sdk import run_simulation
from .model import OrganizationEnsemble,rule_engine
from .run import expand,make_worlds,export_snapshots,save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',default=str(Path(__file__).with_name('large_plan.json')))
    p.add_argument('--engine',choices=['rules','jev'],default='rules');p.add_argument('--allow-paid',action='store_true')
    p.add_argument('--output');p.add_argument('--preview',action='store_true')
    p.add_argument('--max-cost-usd',type=float,default=3);p.add_argument('--max-requests',type=int,default=6000)
    p.add_argument('--max-retries',type=int,default=3);p.add_argument('--timeout',type=float,default=90)
    p.add_argument('--concurrency',type=int,default=2)
    args=p.parse_args();plan=json.loads(Path(args.plan).read_text(encoding='utf-8'));configs=expand(plan)
    sample=make_worlds(configs);periods=next(iter(sample.values())).rounds
    preview=dict(worlds=len(sample),members_per_world=sorted({w.n for w in sample.values()}),periods=periods,
        maximum_jev_decisions=sum(w.pair_budget*2*periods for w in sample.values()),max_retries=args.max_retries,
        timeout_s=args.timeout,concurrency=args.concurrency)
    print(json.dumps(preview,indent=2),flush=True)
    if args.preview:return
    if not args.output:p.error('--output is required.')
    if args.engine=='jev' and not args.allow_paid:p.error('--allow-paid is required.')
    root=Path(args.output);root.mkdir(parents=True,exist_ok=False)
    save(root/'plan-before-calls.json',dict(plan=plan,configs=configs,preview=preview))
    sources=[Path(__file__),Path(__file__).with_name('run.py'),Path(__file__).with_name('model.py')]
    sources+=[Path('orgabm')/name for name in ['sdk.py','memory.py','workforce.py','personas.py','openrouter.py','openrouter_reliable.py']]
    report=dict(status='running',scenario='organizational_conventions',engine_mode=args.engine,python=platform.python_version(),
        groups={},probability_reuse=False,source_hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources})
    started=time.perf_counter();live=None
    try:
        for name in ['uniform','history','notice']+(['jev'] if args.engine=='jev' else []):
            worlds=make_worlds(configs)
            def progress(row,name=name):
                if name=='jev':print(json.dumps(dict(engine=name,**row,usage=live.usage())),flush=True)
            env=OrganizationEnsemble(worlds,progress)
            engine=rule_engine(name) if name!='jev' else ReliableOpenRouterJevEngine(root/'calls',cap_usd=args.max_cost_usd,
                max_requests=args.max_requests,batch_size=32,concurrency=args.concurrency,max_retries=args.max_retries,timeout=args.timeout)
            if name=='jev':live=engine
            try:
                result=run_simulation(env,engine,rounds=periods,seed=202610,output=root/name)
                report['groups'][name]=dict(status=result['status'],decisions=result['decisions'],
                    worlds=export_snapshots(root/f'{name}-snapshots',worlds,env.latest))
            except Exception:
                report['groups'][name]=dict(status='failed',worlds=export_snapshots(root/f'{name}-partial-snapshots',worlds,env.latest))
                raise
            save(root/'verification.json',dict(report,usage=live.usage() if live else {'actual_model_api_calls':0}))
        report['status']='complete'
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__);raise
    finally:
        report.update(elapsed_s=time.perf_counter()-started,usage=live.usage() if live else {'actual_model_api_calls':0})
        save(root/'verification.json',report)
    print(json.dumps(dict(status=report['status'],usage=report['usage']),indent=2))


if __name__=='__main__':main()
