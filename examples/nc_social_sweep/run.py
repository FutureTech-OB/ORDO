"""Run published NC social activation through ORDO and compare author C shells."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import time

from orgabm.sdk import run_simulation
from .model import SocialActivation,native_engine,state_hash
from .sources import COMMIT,REPO,load_sources,build_reference,author_reference


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def cases(plan):
    if set(plan)!={'populations','disorders','seeds'}:raise ValueError('Plan accepts populations, disorders, seeds.')
    configs=[dict(agents=n,disorder=r,seed=s) for n,r,s in itertools.product(plan['populations'],plan['disorders'],plan['seeds'])]
    if not configs or len(configs)>100:raise ValueError('Use 1..100 worlds.')
    for c in configs:SocialActivation(**c)
    return configs


def same_events(expected,actual):
    return len(expected)==len(actual) and all(
        all(a[k]==b[k] for k in ('shell_size','avalanche','remaining')) and math.isclose(a['field'],b['field'],rel_tol=0,abs_tol=1e-12)
        for a,b in zip(expected,actual))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',default=str(Path(__file__).with_name('plan.json')))
    p.add_argument('--cache',default='.buildtmp/nc-social-sources');p.add_argument('--download',action='store_true')
    p.add_argument('--preview',action='store_true');p.add_argument('--output')
    args=p.parse_args();plan=json.loads(Path(args.plan).read_text(encoding='utf-8'));configs=cases(plan)
    if args.preview:
        print(json.dumps(dict(worlds=len(configs),configurations=configs,actual_api_calls=0,
            native_decisions=sum(c['agents'] for c in configs),sdk_round_upper_bound=sum(2*c['agents'] for c in configs)),indent=2));return
    if not args.output:p.error('--output is required.')
    root=Path(args.output);root.mkdir(parents=True,exist_ok=False)
    sources=load_sources(args.cache,args.download);library=build_reference(args.cache)
    report=dict(status='running',paper='Universality, criticality and complexity of information propagation on social media',
        doi='10.1038/s41467-022-28964-8',repository=REPO,upstream_commit=COMMIT,
        plan=plan,worlds=[],python=platform.python_version(),actual_api_calls=0,recorded_cost_usd=0,
        evidence_scope='Native-author RFIM kernel on supplied Gaussian fields, reduced configuration; not empirical fitting/full-paper reproduction.',
        native_reference='Unmodified downloaded C find_seed and next_shell; wrapper only instruments shell records.',
        sources=sources,source_hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in Path(__file__).parent.glob('*.py')},
        reference_library_sha256=hashlib.sha256(library.read_bytes()).hexdigest())
    started=time.perf_counter()
    try:
        for i,c in enumerate(configs):
            w=SocialActivation(**c);author=author_reference(w.fields,library)
            world_dir=root/f'world-{i:03d}';world_dir.mkdir()
            result=run_simulation(w,native_engine(),rounds=2*w.n,seed=c['seed'],output=world_dir/'ordo')
            exact=same_events(author,w.events)
            if not exact:raise AssertionError('ORDO differs from the independent native author dynamics.')
            if not all(w.active) or sum(w.sizes)!=w.n or result['decisions']!=w.n:
                raise AssertionError('Irreversible activation conservation failed.')
            # Independent probability-tape replay, re-creating every local observation.
            class Tape:
                def __init__(self,stream):self.stream=stream
                def decide(self,state,questions):
                    row=json.loads(next(self.stream))
                    if row['state']!=state or row['questions']!=questions:raise AssertionError('Replay observation changed.')
                    return row['probabilities']
                def usage(self):return {'actual_model_api_calls':0,'engine':'saved-probability-replay'}
            rebuilt=SocialActivation(**c)
            with (world_dir/'ordo'/'events.jsonl').open(encoding='utf-8') as stream:
                replay=run_simulation(rebuilt,Tape(stream),rounds=2*w.n,seed=c['seed'])
                if next(stream,None) is not None:raise AssertionError('Unconsumed trace.')
            if replay['metrics']!=result['metrics'] or rebuilt.snapshot()!=w.snapshot():raise AssertionError('Replay differs.')
            row=dict(world=i,**c,decisions=result['decisions'],sdk_rounds=result['completed_rounds'],
                effective_shell_steps=len(w.events),avalanches=len(w.sizes),largest_avalanche=max(w.sizes),
                largest_fraction=max(w.sizes)/w.n,mean_avalanche=w.n/len(w.sizes),
                exact_author_shell_sizes=True,author_fields_max_abs_error=max(abs(a['field']-b['field']) for a,b in zip(author,w.events)),
                all_inputs_and_states_replay_exact=True,elapsed_s=result['elapsed_s'])
            save(world_dir/'author_reference.json',author);save(world_dir/'final_state.json',w.snapshot());save(world_dir/'audit.json',row)
            report['worlds'].append(row);save(root/'verification.json',report)
            print(json.dumps(row),flush=True)
        report['status']='complete'
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__);raise
    finally:
        report['elapsed_s']=time.perf_counter()-started;report['decisions']=sum(r['decisions'] for r in report['worlds'])
        save(root/'verification.json',report)
        if report['worlds']:
            with (root/'summary.csv').open('w',encoding='utf-8',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(report['worlds'][0]));writer.writeheader();writer.writerows(report['worlds'])
    print(json.dumps(dict(status=report['status'],worlds=len(report['worlds']),decisions=report['decisions'],actual_api_calls=0)),flush=True)


if __name__=='__main__':main()
