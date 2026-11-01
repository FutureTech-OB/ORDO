"""Run reduced CMM cases through ORDO and independently launched author kernels."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time

from orgabm.sdk import run_simulation
from .build import DEFAULT,source
from .model import NativeMobility,native_engine,metrics,decode_state,digest,validate


def cases():
    small=[dict(agents=128,rounds=40,seed=seed,memory=memory,rho0=rho0)
        for seed in (7,11,17) for memory in (False,True) for rho0 in (1e-12,10.0)]
    return small+[dict(agents=1000,rounds=40,seed=seed,memory=True,rho0=1e-12) for seed in (7,11,17)]


def reference(config,root):
    exe=(Path(root)/'cmm_reference.exe').resolve()
    provenance=json.loads((Path(root)/'build_manifest.json').read_text(encoding='utf-8'))
    if hashlib.sha256(exe.read_bytes()).hexdigest()!=provenance['cmm_reference.exe']:
        raise ValueError('Native reference differs from its declared build.')
    command=[str(exe),str(config['agents']),str(config['seed']),str(int(config['memory'])),str(config['rho0']),str(config['rounds'])]
    rows=[];final=None;started=time.perf_counter()
    with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) as process:
        for line in process.stdout:
            final=json.loads(line);rows.append(metrics(final,config))
        error=process.stderr.read();status=process.wait(timeout=30)
    if status or len(rows)!=config['rounds']:raise RuntimeError('Native reference failed: '+error[:400])
    return dict(metrics=rows,final=final,elapsed_s=time.perf_counter()-started)


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def run(config,folder,build_root):
    config=validate(config);folder.mkdir();save(folder/'config.json',config)
    ref=reference(config,build_root)
    env=NativeMobility(config,build_root)
    try:
        result=run_simulation(env,native_engine(),rounds=config['rounds'],seed=config['seed'],output=folder/'ordo')
        if result['metrics']!=ref['metrics'] or env.final_values!=ref['final']:
            raise AssertionError('ORDO scheduling changed native model state.')
        with gzip.open(folder/'final_native_state.json.gz','wt',encoding='utf-8') as stream:json.dump(decode_state(env.final_values),stream,separators=(',',':'))
        save(folder/'native-reference.json',dict(metrics=ref['metrics'],elapsed_s=ref['elapsed_s'],final_state_sha256=digest(ref['final'])))
        return dict(config=config,periods=result['completed_rounds'],sdk_control_actions=result['decisions'],
            native_agent_updates=config['agents']*config['rounds'],all_period_metrics_and_state_hashes_exact=True,
            full_final_state_exact=True,native_reference_elapsed_s=ref['elapsed_s'],ordo_elapsed_s=result['elapsed_s'],
            final=result['metrics'][-1],actual_model_api_calls=0,recorded_api_cost_usd=0)
    finally:env.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--build-root',type=Path,default=DEFAULT);p.add_argument('--cases',type=Path)
    a=p.parse_args();selected=json.loads(a.cases.read_text(encoding='utf-8')) if a.cases else cases()
    selected=[validate(x) for x in selected];a.output.mkdir(parents=True,exist_ok=False)
    source_manifest=json.loads((a.build_root/'source_manifest.json').read_text(encoding='utf-8'))
    build_manifest=json.loads((a.build_root/'build_manifest.json').read_text(encoding='utf-8'))
    save(a.output/'source_manifest.json',source_manifest);save(a.output/'build_manifest.json',build_manifest);save(a.output/'cases.json',selected)
    report=dict(status='running',source_doi='10.1038/s43588-021-00160-6',python=platform.python_version(),
        cases=[],actual_model_api_calls=0,recorded_api_cost_usd=0,
        source_hashes={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in Path(__file__).parent.glob('*') if x.is_file()},
        claim='Reduced author-kernel portability via ORDO; not published 30,000-agent,20,000-period urban-scaling validation.')
    started=time.perf_counter()
    try:
        for i,c in enumerate(selected):
            row=run(c,a.output/f'world-{i:03d}',a.build_root);report['cases'].append(row)
            print(json.dumps(dict(world=i,config=c,exact=True,native_agent_updates=row['native_agent_updates'])),flush=True)
        report['status']='complete'
    except Exception as e:report.update(status='failed',error_type=type(e).__name__);raise
    finally:
        report['elapsed_s']=time.perf_counter()-started
        report['native_agent_updates']=sum(x['native_agent_updates'] for x in report['cases'])
        report['sdk_control_actions']=sum(x['sdk_control_actions'] for x in report['cases'])
        save(a.output/'verification.json',report)
        with (a.output/'summary.csv').open('w',newline='',encoding='utf-8') as stream:
            fields=['agents','rounds','seed','memory','rho0','native_agent_updates','ordo_elapsed_s','occupied_sites','mean_memory_locations','mean_toroidal_radius','spatial_concentration']
            writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader()
            for row in report['cases']:writer.writerow({**row,**row['config'],**row['final']})


if __name__=='__main__':main()
