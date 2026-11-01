"""Explicit small live Jev trials through ORDO; credentials only from the environment.

python -m examples.llm_abm_cookbook.live_openrouter --allow-paid --output runs/openrouter-jev-small
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import time

from orgabm.openrouter import OpenRouterJevEngine
from orgabm.sdk import run_simulation
from .environments import NamingGame, MajorityOpinion


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-paid',action='store_true')
    parser.add_argument('--output',required=True)
    parser.add_argument('--updates',type=int,default=6,help='Pair interactions / single-person updates per scene.')
    parser.add_argument('--max-requests',type=int,default=20,help='Shared allowance across both scenes.')
    parser.add_argument('--max-cost-usd',type=float,default=0.01,help='Shared client allowance across both scenes.')
    parser.add_argument('--seed',type=int,default=7)
    args=parser.parse_args()
    if not args.allow_paid: parser.error('Explicit --allow-paid is required.')
    if not 1<=args.updates<=1000: parser.error('Use 1..1000 updates for this bounded trial.')
    if args.max_requests<2*args.updates: parser.error('The two scenes require two requests per update count.')
    root=Path(args.output); root.mkdir(parents=True,exist_ok=False)
    engine=OpenRouterJevEngine(root/'calls',max_requests=args.max_requests,cap_usd=args.max_cost_usd,
                               batch_size=64,concurrency=1)
    report=dict(status='running',evidence='fresh_Jev_decisions_through_ORDO_SDK',python=platform.python_version(),
        seed=args.seed,probability_reuse=False,source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path('orgabm/openrouter.py'),Path('orgabm/sdk.py'),Path(__file__),Path(__file__).with_name('environments.py'))},
        limits='Connectivity and execution trial; too short for convergence, behavioral fidelity or performance comparisons.',cases=[])
    started=time.perf_counter()
    try:
        for name,world in [('naming',NamingGame(agents=24,options=list('QMXYFJPRCD'),seed=args.seed)),
                           ('opinion',MajorityOpinion(agents=50,seed=args.seed))]:
            result=run_simulation(world,engine,rounds=args.updates,seed=args.seed,output=root/name)
            report['cases'].append(dict(scene=name,status=result['status'],agents=world.n,
                updates=result['completed_rounds'],decisions=result['decisions'],last_metrics=result['metrics'][-1]))
        report['status']='complete'
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__)
        raise
    finally:
        report['usage']=engine.usage(); report['elapsed_s']=time.perf_counter()-started
        (root/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
