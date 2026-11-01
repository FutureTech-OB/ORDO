"""Run all 882 author public-capsule native days, then an untouched full reference."""
import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import csv
import json
from pathlib import Path
import platform
import random
import time
import networkx as nx
import numpy as np
from .source import load,author_class,digest,graph_record,memory_record


def save(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def rng_json(state):
    return dict(generator=state[0],keys=state[1].tolist(),position=state[2],has_gauss=state[3],cached_gaussian=state[4])


def execute(data,initial_rng,out,daily):
    source,notebook,dist,dates,memory,params,meta=data
    cls,patch_sha=author_class(source,dist,dates,daily=daily)
    np.random.set_state(initial_rng);random.seed(42)
    phase_results=[];rows=[];graphs_by_phase=[];prefix=None;states=[]
    started=time.perf_counter()
    for p in meta['phases']:
        if p['id']=='nochange_counterfactual':memory=deepcopy(prefix)
        distances={e:(2000,v[1]) for e,v in dist.items()} if p['remote'] else dist
        estimator=cls(memory,distances,**params)
        # A private clone forecasts exactly the normal-size vector without consuming source RNG.
        clone=np.random.RandomState();clone.set_state(np.random.get_state())
        shifts=clone.normal(scale=params['normal_scale'],size=p['days'])
        states.append(dict(phase=p['id'],rng_before=rng_json(np.random.get_state())))
        logname='native_author_stdout.log' if daily else 'untouched_author_stdout.log'
        with (out/logname).open('a',encoding='utf-8') as log,redirect_stdout(log):
            if daily:
                iterator=estimator.transform(None,start=p['start'],end=p['end']);produced=[]
                while True:
                    try:graph=next(iterator)
                    except StopIteration:break
                    day=p['start']+len(produced);produced.append(graph.copy())
                    if len(produced)%25==0:
                        save(out/'progress.json',dict(status='running',phase=p['id'],phase_completed_days=len(produced),phase_total_days=p['days'],completed_days=len(rows)+len(produced),elapsed_s=time.perf_counter()-started))
            else:
                native_bridges,native_comps,produced=estimator.transform(None,start=p['start'],end=p['end'])
        memory=estimator.mem_dict
        if p['id']=='shared_colocated_prefix':prefix=deepcopy(memory)
        phase_rows=[]
        for k,g in enumerate(produced):
            small=g.subgraph([n for n in g if len(g[n])<100]);shift=int(shifts[k]);day=p['start']+k
            bridges=len(list(nx.local_bridges(small,with_span=False)))
            components=nx.number_connected_components(small)
            if not daily:
                assert bridges==int(native_bridges[k]) and components==int(native_comps[k])
            row=dict(phase=p['id'],author_day_index=day,date=dates[day].date().isoformat(),
                first_draw=50+shift,second_draw=20+shift,selected_edges=g.number_of_edges(),
                first_candidates=len(estimator.all_edges),second_candidates=len(estimator.all_edges)-(50+shift),
                weak_ties=bridges,components=components,clustering=nx.average_clustering(g),
                graph_sha256=digest(graph_record(g)))
            assert row['selected_edges']==row['first_draw']+row['second_draw']
            phase_rows.append(row)
        rows.extend(phase_rows);graphs_by_phase.append(produced)
        phase_results.append(dict(**p,days_completed=len(produced),memory_sha256=digest(memory_record(memory)),
            merged_weak_tie_history_sha256=digest([[list(e),[(d.isoformat(),w) for d,w in entries]] for e,entries in estimator.merged_num_bridges.items()]),
            selected_edges=sum(r['selected_edges'] for r in phase_rows),candidate_scores=sum(r['first_candidates']+r['second_candidates'] for r in phase_rows),
            mean_weak_ties=sum(r['weak_ties'] for r in phase_rows)/len(phase_rows),
            mean_clustering=sum(r['clustering'] for r in phase_rows)/len(phase_rows)))
        save(out/('progress.json' if daily else 'reference_progress.json'),dict(status='running',phase=p['id'],completed_days=len(rows),total_days=882,elapsed_s=time.perf_counter()-started))
    # Exact author weekly IOU uses raw NetworkX edge orientation, not canonical pairs.
    paths={name:[g for index in indices for g in graphs_by_phase[index]]
           for name,indices in [('remote_then_return',[0,1,2]),('continuous_colocation',[0,3])]}
    path_metrics={}
    for name,graphs in paths.items():
        iou=[];canonical_iou=[]
        for old,new in zip(graphs,graphs[5:]):
            a=set(old.edges);b=set(new.edges);iou.append(len(a&b)/len(a|b))
            ca={tuple(sorted(e)) for e in old.edges};cb={tuple(sorted(e)) for e in new.edges}
            canonical_iou.append(len(ca&cb)/len(ca|cb))
        path_metrics[name]=dict(days=len(graphs),author_weekly_iou=iou,canonical_undirected_iou_diagnostic=canonical_iou,
            graph_series_sha256=digest([graph_record(g) for g in graphs]))
    return dict(phases=phase_results,rows=rows,path_metrics=path_metrics,rng_states=states,
                last_memory=memory_record(memory),method_ast_sha256=patch_sha)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    p.add_argument('--cache',default='.buildtmp/ncs-colocation-source');p.add_argument('--download',action='store_true')
    p.add_argument('--numpy-seed',type=int,default=20261030,help='New recorded realization; original NumPy state was not supplied by author.')
    args=p.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    data=load(args.cache,args.download);meta=data[-1]
    np.random.seed(args.numpy_seed);initial=np.random.get_state()
    plan=dict(**meta,numpy_seed_for_this_new_realization=args.numpy_seed,numpy_initial_state=rng_json(initial),
        total_native_days=882,unique_paths=2,each_full_path_days=467,
        private_mit_full_reproduction='Blocked: original 2,834-person email network and complete distances not public. Public notebook demo is executed in full, without downsampling.',
        python=platform.python_version(),numpy=np.__version__,networkx=nx.__version__,
        local_source_hashes={str(f.name):__import__('hashlib').sha256(f.read_bytes()).hexdigest() for f in Path(__file__).parent.glob('*.py')})
    save(out/'plan-before-run.json',plan);save(out/'progress.json',dict(status='starting',completed_days=0,total_days=882))
    started=time.perf_counter();report=dict(status='running',scope=plan['scope'],original_private_data_missing=True,actual_api_calls=0)
    try:
        native=execute(data,initial,out,True);save(out/'native_results.json',native)
        # Re-load fresh data; no graph or memory state is reused across the independent reference.
        reference=execute(load(args.cache),initial,out,False);save(out/'untouched_reference.json',reference)
        checks={k:native[k]==reference[k] for k in ['phases','rows','path_metrics','rng_states','last_memory']}
        if not all(checks.values()):raise AssertionError('Daily instrumentation differs from the untouched original author method.')
        report.update(status='complete',checks=checks,native_days=len(native['rows']),
            selected_edges=sum(r['selected_edges'] for r in native['rows']),
            full_candidate_score_queries=sum(r['first_candidates']+r['second_candidates'] for r in native['rows']),
            phases=native['phases'],path_metrics=native['path_metrics'])
        with (out/'daily_metrics.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(native['rows'][0]));w.writeheader();w.writerows(native['rows'])
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__);raise
    finally:
        report['elapsed_s']=time.perf_counter()-started;save(out/'verification.json',report)
        save(out/'progress.json',dict(status=report['status'],completed_days=report.get('native_days'),total_days=882,elapsed_s=report['elapsed_s']))
    print(json.dumps({k:report[k] for k in ['status','native_days','selected_edges','full_candidate_score_queries','elapsed_s','checks']},indent=2))


if __name__=='__main__':main()
