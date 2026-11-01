"""Generate fresh author PedNav routes through ORDO and check direct native calls."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np
from orgabm.sdk import run_simulation
from .model import AuthorNavigation,PedNavTrips,native_engine,graph_library
from .sources import DEFAULT,DOI,load_sources


def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def reference(author,config):
    """Call the original methods directly, without the SDK or route wrapper."""
    routes=[];old=np.random.get_state();started=time.perf_counter()
    try:
        fn=author.navigation.Stochastic_Vector_Path if config['kind']=='vector' else author.navigation.Stochastic_Shortest_Path
        for i,trip in enumerate(author.human[:config['trip_limit']]):
            np.random.seed((config['seed']+i)%2**32)
            with np.errstate(divide='ignore',invalid='ignore'):
                routes.append([int(x) for x in fn(trip['destination'],[trip['origin']],config['sigma'])[0]])
    finally:np.random.set_state(old)
    return routes,time.perf_counter()-started


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',type=Path,default=DEFAULT)
    p.add_argument('--download',action='store_true');p.add_argument('--trip-limit',type=int,default=20)
    p.add_argument('--cases',type=Path,help='Optional editable JSON list of kind,sigma,seed,trip_limit.')
    a=p.parse_args();manifest=load_sources(a.cache,a.download);author=AuthorNavigation(a.cache)
    cases=json.loads(a.cases.read_text(encoding='utf-8')) if a.cases else [
        dict(kind=kind,sigma=sigma,seed=seed,trip_limit=a.trip_limit)
        for kind in ('vector','shortest') for sigma in (0.0,0.7) for seed in (7,11,17)]
    for c in cases:PedNavTrips(author,**c)
    a.output.mkdir(parents=True,exist_ok=False);save(a.output/'cases.json',cases);save(a.output/'source_manifest.json',manifest)
    report=dict(status='running',doi=DOI,source=author.describe(),python=platform.python_version(),
        numpy=np.__version__,igraph=graph_library().__version__,cases=[],actual_model_api_calls=0,recorded_api_cost_usd=0,
        claim='Fresh author-native independent pedestrian route component via ORDO. Not coupled social ABM, full-paper empirical replication, or Jev inference.',
        source_hashes={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in Path(__file__).parent.glob('*.py')})
    started=time.perf_counter();all_rows=[]
    try:
        for i,c in enumerate(cases):
            folder=a.output/f'world-{i:03d}';folder.mkdir();save(folder/'config.json',c)
            ref,elapsed=reference(author,c);env=PedNavTrips(author,**c)
            result=run_simulation(env,native_engine(),rounds=c['trip_limit'],seed=c['seed'],output=folder/'ordo')
            if env.routes!=ref:raise AssertionError('SDK route paths differ from direct author calls.')
            with gzip.open(folder/'generated_routes.json.gz','wt',encoding='utf-8') as stream:json.dump(env.routes,stream,separators=(',',':'))
            ref_sha=hashlib.sha256(json.dumps(ref,separators=(',',':')).encode()).hexdigest()
            save(folder/'native-reference.json',dict(all_paths_exact=True,route_count=len(ref),routes_sha256=ref_sha,elapsed_s=elapsed))
            row=dict(config=c,all_paths_exact=True,native_route_samples=len(env.routes),sdk_control_actions=result['decisions'],
                reference_route_samples=len(ref),native_reference_elapsed_s=elapsed,ordo_elapsed_s=result['elapsed_s'],
                mean_detour_ratio=float(np.mean([x['detour_ratio'] for x in env.trajectory])),
                mean_length_m=float(np.mean([x['length_m'] for x in env.trajectory])))
            report['cases'].append(row)
            all_rows.extend(dict(world=i,**c,**trip) for trip in env.trajectory)
            print(json.dumps(dict(world=i,**c,exact=True,mean_detour_ratio=row['mean_detour_ratio'])),flush=True)
        report['status']='complete'
    except Exception as e:report.update(status='failed',error_type=type(e).__name__);raise
    finally:
        report['elapsed_s']=time.perf_counter()-started
        report['native_route_samples']=sum(x['native_route_samples'] for x in report['cases'])
        report['reference_route_samples']=sum(x['reference_route_samples'] for x in report['cases'])
        report['sdk_control_actions']=sum(x['sdk_control_actions'] for x in report['cases'])
        with (a.output/'routes.csv').open('w',newline='',encoding='utf-8') as stream:
            if all_rows:
                writer=csv.DictWriter(stream,fieldnames=list(all_rows[0]));writer.writeheader();writer.writerows(all_rows)
        report['output_sha256']={str(x.relative_to(a.output)):hashlib.sha256(x.read_bytes()).hexdigest()
            for x in a.output.rglob('*') if x.is_file()}
        save(a.output/'verification.json',report)


if __name__=='__main__':main()
