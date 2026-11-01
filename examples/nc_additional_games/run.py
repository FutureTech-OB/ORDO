"""Replay native social-reward evolution with the ORDO Environment contract."""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
import platform
from statistics import mean
import time
from orgabm.sdk import run_simulation
from .model import SocialRewarding,NativeEngine,direct_reference,source_manifest,COMMIT,DOI


def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',default=str(Path(__file__).with_name('plan.json')))
    parser.add_argument('--output');parser.add_argument('--preview',action='store_true');args=parser.parse_args()
    plan=json.loads(Path(args.plan).read_text(encoding='utf-8'))
    cases=[dict(plan['base'],information=l,mutation=m,seed=s) for l,m,s in itertools.product(plan['information'],plan['mutation'],plan['seeds'])]
    if not 1<=len(cases)<=100:raise ValueError('Use 1..100 worlds.')
    preview=dict(worlds=len(cases),members=sorted({c['agents'] for c in cases}),updates_per_world=sorted({c['rounds'] for c in cases}),
        native_ordo_decisions=sum(c['rounds'] for c in cases),actual_model_api_calls=0)
    print(json.dumps(preview),flush=True)
    if args.preview:return
    if not args.output:parser.error('--output is required')
    root=Path(args.output);root.mkdir(parents=True,exist_ok=False)
    save(root/'plan.json',plan);save(root/'sources.json',source_manifest())
    report=dict(status='running',doi=DOI,commit=COMMIT,python=platform.python_version(),worlds=[],
        decisions=0,actual_model_api_calls=0,recorded_cost_usd=0,all_source_states_exact=True,all_source_metrics_exact=True,
        source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
        scope='Native two-player reputation/reward simulation, reduced 3,000-update grid; not billion-step stationary sweeps or new LLM judgment.')
    started=time.perf_counter()
    try:
        with (root/'trajectories.csv').open('w',newline='',encoding='utf-8') as stream:
            writer=csv.writer(stream);writer.writerow(['world','information','mutation','seed','update','cooperation','social_rewarding_share','state_sha256'])
            for i,config in enumerate(cases):
                world=SocialRewarding(**config);reference=direct_reference(config)
                result=run_simulation(world,NativeEngine(world),rounds=config['rounds'],seed=config['seed'],output=root/f'w{i:03d}')
                for metric,ref in zip(result['metrics'],reference):
                    if any(metric[k]!=v for k,v in ref.items()):raise AssertionError('Author native update and ORDO differ.')
                    writer.writerow([i,config['information'],config['mutation'],config['seed'],metric['update'],
                        metric['post_cooperation'],metric['social_rewarding_share'],metric['state_sha256']])
                tail=result['metrics'][len(result['metrics'])*2//3:]
                report['worlds'].append(dict(world=i,config=config,final=result['metrics'][-1],
                    last_third_mean_cooperation=mean(m['post_cooperation'] for m in tail),
                    last_third_mean_social_rewarding=mean(m['social_rewarding_share'] for m in tail),elapsed_s=result['elapsed_s']))
                report['decisions']+=result['decisions']
                print(json.dumps(dict(completed=i+1,total=len(cases),information=config['information'],mutation=config['mutation'],seed=config['seed'])),flush=True)
        report['status']='complete'
    except Exception as error:report.update(status='failed',error_type=type(error).__name__);raise
    finally:report['elapsed_s']=time.perf_counter()-started;save(root/'verification.json',report)
    print(json.dumps(dict(status=report['status'],worlds=len(report['worlds']),decisions=report['decisions'],elapsed_s=report['elapsed_s'],actual_model_api_calls=0)),flush=True)


if __name__=='__main__':main()
