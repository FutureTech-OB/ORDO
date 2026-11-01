"""Run unchanged-length native repeats in isolated one-thread Julia processes.

No model API calls. Completed repeat files are durable; unfinished repeats can
be restarted from their declared seed without claiming mid-function recovery.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time


def save(p,v):
    temp=p.with_suffix('.tmp');temp.write_text(json.dumps(v,indent=2),encoding='utf-8');os.replace(temp,p)


def main():
    p=argparse.ArgumentParser();p.add_argument('--julia',required=True);p.add_argument('--output',required=True)
    p.add_argument('--workers',type=int,default=16);p.add_argument('--full-donation-grid',action='store_true');a=p.parse_args()
    if not 1<=a.workers<=20:raise ValueError('Use at most20 one-thread jobs on shared research server.')
    out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
    deltas=[.01,.1,.5] if a.full_donation_grid else [.01]
    peripheries=list(range(100,161,10)) if a.full_donation_grid else [100]
    jobs=[dict(id=f'donation_d{d}_np{np}_{mode}_r{rep:02d}',nc=8,np=np,u=.05,tau=1.,delta=d,network=mode,
        seed=2026103000+rep,max_iter=100_000_000,repeat=rep)
        for d in deltas for np in peripheries for mode in ('dynamic','static') for rep in range(10)]
    plan=dict(doi='10.1038/s43588-026-01068-9',figure='Published Extended Data Fig.2 donation panels a-c',
        comparison='dynamic core/periphery vs one isomorphic static counterpart',
        construction='Figure3 published-caption reconstruction; original archive omitted full figure-generation workflows',
        kernel='Author Simulation.jl, with numerical/RNG-state observation hook only',
        max_iter_per_repeat=100_000_000,repeats_per_point=10,burnin_fraction=.05,
        jobs=jobs,total_events=sum(j['max_iter'] for j in jobs),workers=a.workers,
        api_calls=0,paid_cost_usd=0,scope='Donation-game panels only; other games and original analytical Figure3 are not represented by these Monte Carlo jobs.')
    if (out/'plan.json').exists():
        if json.loads((out/'plan.json').read_text())!=plan:raise ValueError('Existing frozen plan differs.')
    else:save(out/'plan.json',plan)
    pending=[j for j in jobs if not (out/(j['id']+'.result.json')).exists()];running={};failed=[];started=time.time()
    env=dict(os.environ,JULIA_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    driver=Path(__file__).with_name('run_native.jl').resolve()
    while pending or running:
        while pending and len(running)<a.workers:
            j=pending.pop(0);prefix=out/j['id'];log=(out/(j['id']+'.stdout.log')).open('ab')
            cmd=[a.julia,'--startup-file=no',str(driver),str(j['nc']),str(j['np']),str(j['u']),str(j['tau']),str(j['delta']),j['network'],str(j['seed']),str(j['max_iter']),str(prefix)]
            proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env)
            running[j['id']]=(proc,log,j)
        for key,(proc,log,j) in list(running.items()):
            status=proc.poll()
            if status is not None:
                log.close();del running[key]
                if status:failed.append(dict(id=key,exit_code=status))
        completed=[j for j in jobs if (out/(j['id']+'.result.json')).exists()]
        save(out/'status.json',dict(status='running' if pending or running else 'failed' if failed else 'complete',
            coordinator_pid=os.getpid(),elapsed_s=time.time()-started,total_jobs=len(jobs),completed_jobs=len(completed),
            completed_full_events=sum(j['max_iter'] for j in completed),pending_jobs=len(pending),
            running=[dict(id=key,pid=v[0].pid) for key,v in running.items()],failed=failed))
        if pending or running:time.sleep(5)
    # Never merge a single repeat into a completed ten-repeat point.
    points=[]
    for d in deltas:
        for np in peripheries:
            for mode in ('dynamic','static'):
                group=[j for j in jobs if j['delta']==d and j['np']==np and j['network']==mode]
                files=[out/(j['id']+'.result.json') for j in group]
                values=[json.loads(f.read_text())['cooperation_frequency'] for f in files if f.exists()]
                points.append(dict(delta=d,np=np,network=mode,completed_repeats=len(values),required_repeats=10,
                    status='complete' if len(values)==10 else 'incomplete',mean_cooperation=sum(values)/len(values) if values else None))
    save(out/'point_summary.json',points)


if __name__=='__main__':main()
