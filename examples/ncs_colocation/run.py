"""Execute the published NCS co-location network model through ORDO."""
import argparse
import csv
import itertools
import json
from pathlib import Path
import platform
import time
import networkx as nx
import numpy as np
from orgabm.sdk import run_simulation
from .sources import checkout, digest, COMMIT, URL, PARAMETERS
from .model import ColocationEnvironment, native_engine, reference, memory_state, state_hash


def save(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',default=str(Path(__file__).with_name('plan.json')))
    p.add_argument('--cache',default='.buildtmp/ncs-colocation-source')
    p.add_argument('--download',action='store_true');p.add_argument('--output',required=True)
    a=p.parse_args();plan=json.loads(Path(a.plan).read_text(encoding='utf-8'))
    if set(plan)!={'populations','seeds','policies','phase_days'}:raise ValueError('Unexpected plan fields.')
    configs=[dict(population=n,seed=s,policy=policy,lengths=tuple(plan['phase_days']))
             for n,s,policy in itertools.product(plan['populations'],plan['seeds'],plan['policies'])]
    if not 1<=len(configs)<=100:raise ValueError('Use 1..100 configurations.')
    source=checkout(a.cache,a.download);out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
    files=['code/SimulationsSubmission.ipynb','code/dist_dict_demo.p','code/dates_fall2021.p',
           'code/undir_semiactive_demo.p','code/LICENSE']
    report=dict(status='running',paper='The effect of co-location on human communication networks',
        journal='Nature Computational Science',doi='10.1038/s43588-022-00296-z',
        source_url=URL,source_doi='10.24433/CO.5754680.v1',upstream_commit=COMMIT,
        upstream_files={f:digest(source/f) for f in files},plan=plan,author_parameters=PARAMETERS,
        python=platform.python_version(),numpy=np.__version__,networkx=nx.__version__,
        actual_api_calls=0,recorded_cost_usd=0,worlds=[],
        source_hashes={f.relative_to(Path(__file__).resolve().parents[2]).as_posix():digest(f)
                       for f in [*Path(__file__).resolve().parent.glob('*.py'),Path('orgabm/sdk.py').resolve(),Path('orgabm/randomness.py').resolve()]},
        scope='Author native organizational-network simulation on public demo and induced subset; reduced horizons; not the private MIT dataset or full empirical replication.',
        integration='ORDO native Environment prepare/advance with empty DecisionBatch; native coupled stochastic edge selection preserved. This is not validation of an external decision engine.')
    started=time.perf_counter();trajectory=[]
    try:
        for i,c in enumerate(configs):
            world_start=time.perf_counter();world=ColocationEnvironment(source,**c)
            folder=out/f'world-{i:03d}';folder.mkdir()
            sdk=run_simulation(world,native_engine(),rounds=sum(c['lengths']),seed=c['seed'],output=folder/'ordo')
            author=reference(source,**c)
            checks=dict(all_daily_graphs_exact=author['graphs']==world.graphs,
                        all_daily_weak_ties_exact=author['weak_ties']==[r['weak_ties'] for r in world.records],
                        all_daily_components_exact=author['components']==[r['components'] for r in world.records],
                        final_full_edge_memory_exact=author['memory']==memory_state(world.memory))
            boundaries=np.cumsum(c['lengths'])
            checks['all_phase_memories_exact']=author['phase_memory_sha256']==[world.records[int(t)-1]['memory_sha256'] for t in boundaries]
            if not all(checks.values()):raise AssertionError('ORDO native adapter differs from the untouched author transform.')
            # A second reconstruction tests local recorded inputs and final state.
            class Tape:
                def __init__(self,stream):self.stream=stream
                def decide(self,state,questions):
                    row=json.loads(next(self.stream))
                    if row['state']!=state or row['questions']!=questions:raise AssertionError('Replay request changed.')
                    return row['probabilities']
                def usage(self):return {'engine':'native-trace-reexecution','actual_api_calls':0}
            rebuilt=ColocationEnvironment(source,**c)
            with (folder/'ordo/events.jsonl').open(encoding='utf-8') as stream:
                replay=run_simulation(rebuilt,Tape(stream),rounds=sum(c['lengths']),seed=c['seed'])
                if next(stream,None) is not None:raise AssertionError('Extra trace rows.')
            checks['saved_inputs_and_native_reexecution_exact']=replay['metrics']==sdk['metrics'] and rebuilt.snapshot()==world.snapshot()
            if not all(checks.values()):raise AssertionError('Native trace re-execution differs.')
            means={}
            for phase in range(3):
                rows=[r for r in world.records if r['phase']==phase]
                for key in ('weak_ties','clustering','edges'):
                    means[f'phase{phase}_{key}_mean']=sum(r[key] for r in rows)/len(rows)
            row=dict(world=i,population=c['population'],seed=c['seed'],policy=c['policy'],
                     native_days=sum(c['lengths']),native_selected_edges=world.native_edge_draws,
                     external_decisions=sdk['decisions'],**checks,**means,elapsed_s=time.perf_counter()-world_start)
            save(folder/'author_reference.json',author);save(folder/'final_state.json',world.snapshot());save(folder/'audit.json',row)
            report['worlds'].append(row);trajectory.extend(dict(world=i,seed=c['seed'],policy=c['policy'],**r) for r in world.records)
            save(out/'verification.json',report);print(json.dumps(row),flush=True)
        report['status']='complete'
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__);raise
    finally:
        report['elapsed_s']=time.perf_counter()-started
        report['native_days']=sum(w['native_days'] for w in report['worlds'])
        report['native_selected_edges']=sum(w['native_selected_edges'] for w in report['worlds'])
        save(out/'verification.json',report)
        for filename,rows in [('summary.csv',report['worlds']),('trajectories.csv',trajectory)]:
            if rows:
                with (out/filename).open('w',newline='',encoding='utf-8') as stream:
                    writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(dict(status=report['status'],worlds=len(report['worlds']),native_days=report['native_days'],native_selected_edges=report['native_selected_edges'],elapsed_s=report['elapsed_s'])),flush=True)


if __name__=='__main__':main()
