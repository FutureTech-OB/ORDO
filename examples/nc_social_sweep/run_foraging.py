"""Run NC collective foraging via ORDO with exact original-author comparisons."""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
import platform
import time
import numpy as np

from orgabm.sdk import run_simulation
from .foraging import ForagingEnvironment,AuthorPolicyEngine,plain,digest,slice_record
from .foraging_sources import COMMIT,REPO,load_sources,load_author


def save(file,value):
    file.write_text(json.dumps(plain(value),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def cases(plan):
    if set(plan)!={'environments','policies','seeds','agents','steps','mining_steps'}:raise ValueError('Unknown foraging plan fields.')
    configs=[dict(environment=e,policy=p,seed=s,agents=plan['agents'],steps=plan['steps'],mining_steps=plan['mining_steps'])
        for e,p,s in itertools.product(plan['environments'],plan['policies'],plan['seeds'])]
    if not configs or len(configs)>100:raise ValueError('Use 1..100 foraging worlds.')
    return configs


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',default=str(Path(__file__).with_name('foraging_plan.json')))
    p.add_argument('--cache',default='.buildtmp/nc-foraging-source');p.add_argument('--download',action='store_true')
    p.add_argument('--preview',action='store_true');p.add_argument('--output')
    a=p.parse_args();plan=json.loads(Path(a.plan).read_text(encoding='utf-8'));configs=cases(plan)
    if a.preview:
        print(json.dumps(dict(worlds=len(configs),configurations=configs,actual_api_calls=0),indent=2));return
    if not a.output:p.error('--output is required.')
    np.seterr(divide='ignore',invalid='ignore') # Original visibility code divides 0/0 at the focal position, then explicitly includes it.
    sources=load_sources(a.cache,a.download);task,sim,transform=load_author(a.cache)
    root=Path(a.output);root.mkdir(parents=True,exist_ok=False)
    files=[Path(__file__),Path(__file__).with_name('foraging.py'),Path(__file__).with_name('foraging_sources.py'),Path('orgabm/sdk.py'),Path('orgabm/randomness.py')]
    report=dict(status='running',paper='Adaptive mechanisms of social and asocial learning in immersive collective foraging',
        doi='10.1038/s41467-025-58365-6',upstream_repository=REPO,upstream_commit=COMMIT,
        sources=sources,transformation=transform,plan=plan,worlds=[],actual_api_calls=0,recorded_cost_usd=0,
        python=platform.python_version(),numpy=np.__version__,source_hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
        evidence_scope='Original author State/AgentView/Policy and original run-loop mechanics; exact seeded native stochastic parity. Two selected published maps and reduced repetition grid, not full empirical fit or 12,000-world study.',
        native_decision_records='one-hot choices from original author Policy.sample_next_cell and PCG64; no fresh LLM decisions')
    started=time.perf_counter()
    try:
        for i,c in enumerate(configs):
            folder=root/f'world-{i:03d}';folder.mkdir();world=ForagingEnvironment(task,sim,a.cache,**c)
            result=run_simulation(world,AuthorPolicyEngine(world),rounds=c['agents']*c['steps'],seed=c['seed'],output=folder/'ordo')
            author=world.reference();actual=world.final_result
            if actual is None:raise AssertionError('Goal-choice horizon insufficient; world is incomplete.')
            exact_stats=plain(actual.stats)==plain(author.stats)
            actual_slices=[digest(slice_record(x)) for x in actual.sim_slices];author_slices=[digest(slice_record(x)) for x in author.sim_slices]
            if not exact_stats or actual_slices!=author_slices:raise AssertionError('ORDO changed the original author trajectory.')
            class Tape:
                def __init__(self,stream):self.stream=stream
                def decide(self,state,questions):
                    row=json.loads(next(self.stream))
                    if row['state']!=state or row['questions']!=questions:raise AssertionError('Replayed local observation changed.')
                    return row['probabilities']
                def usage(self):return {'actual_model_api_calls':0,'engine':'saved-native-action-replay'}
            rebuilt=ForagingEnvironment(task,sim,a.cache,**c)
            with (folder/'ordo'/'events.jsonl').open(encoding='utf-8') as stream:
                replay=run_simulation(rebuilt,Tape(stream),rounds=c['agents']*c['steps'],seed=c['seed'])
                if next(stream,None) is not None:raise AssertionError('Unused source observations.')
            if replay['metrics']!=result['metrics'] or plain(rebuilt.final_result.stats)!=plain(actual.stats):raise AssertionError('Saved-action replay changed world.')
            final=actual.sim_slices[-1];payoffs=[sum(int(s['reward']) for s in actual.stats if s['agent']==who) for who in range(c['agents'])]
            row=dict(world=i,**c,goal_decisions=result['decisions'],sdk_rounds=result['completed_rounds'],
                physical_steps=len(actual.sim_slices),total_rewards=sum(payoffs),rewards_by_agent=payoffs,
                revealed_blocks=int(final.state.revealed_map.sum()),exact_author_step_statistics=True,
                exact_author_full_states=True,exact_local_observation_replay=True,elapsed_s=result['elapsed_s'])
            save(folder/'step_statistics.json',actual.stats);save(folder/'state_hashes.json',dict(author=author_slices,ordo=actual_slices))
            save(folder/'final_state.json',slice_record(final));save(folder/'audit.json',row)
            report['worlds'].append(row);save(root/'verification.json',report);print(json.dumps(row),flush=True)
        report['status']='complete'
    except Exception as error:report.update(status='failed',error_type=type(error).__name__);raise
    finally:
        report['elapsed_s']=time.perf_counter()-started;report['decisions']=sum(x['goal_decisions'] for x in report['worlds'])
        save(root/'verification.json',report)
        if report['worlds']:
            with (root/'summary.csv').open('w',encoding='utf-8',newline='') as stream:
                rows=[dict(x,rewards_by_agent=json.dumps(x['rewards_by_agent'])) for x in report['worlds']]
                writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(dict(status=report['status'],worlds=len(report['worlds']),decisions=report['decisions'],actual_api_calls=0)),flush=True)


if __name__=='__main__':main()
