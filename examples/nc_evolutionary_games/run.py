"""Run pinned author strategies and reduced well-mixed evolution via ORDO.

python -m examples.nc_evolutionary_games.run --preview
python -m examples.nc_evolutionary_games.run --output runs/nc-games
"""
import argparse
from collections import defaultdict
import csv
import hashlib
import itertools
import json
from pathlib import Path
import platform
from statistics import mean
import time
import numpy as np

from orgabm.sdk import run_simulation
from orgabm.staged import run_staged_simulation
from .model import RepeatedGame,AuthorStrategyEngine,direct_reference,source_manifest,NAMES,digest,COMMIT,DOI
from .evolution import WellMixedEvolution,NativeImitation,evolution_reference


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',default=str(Path(__file__).with_name('plan.json')))
    p.add_argument('--output');p.add_argument('--preview',action='store_true');args=p.parse_args()
    plan=json.loads(Path(args.plan).read_text(encoding='utf-8'))
    strategy_ids=plan['strategies'];seeds=plan['seeds'];flags=plan['first_move_flags'];rounds=plan['game_rounds'];ec=plan['evolution']
    if not 1<=len(strategy_ids)<=len(NAMES) or len(set(strategy_ids))!=len(strategy_ids) or any(s not in NAMES for s in strategy_ids):raise ValueError('Invalid strategy set.')
    count=len(strategy_ids)**2*len(seeds)*len(flags)
    if count>3000:raise ValueError('Use at most 3,000 pair worlds per run.')
    preview=dict(pair_worlds=count,evolution_worlds=len(seeds)*len(ec['selection'])*len(ec['with_mtbr']),
        pair_decisions=count*rounds*2,evolution_decisions=len(seeds)*len(ec['selection'])*len(ec['with_mtbr'])*ec['agents']*ec['rounds'],
        actual_model_api_calls=0)
    print(json.dumps(preview),flush=True)
    if args.preview:return
    if not args.output:p.error('--output is required')
    root=Path(args.output);root.mkdir(parents=True,exist_ok=False);(root/'pairs').mkdir();(root/'evolution').mkdir()
    save(root/'plan.json',plan);save(root/'sources.json',source_manifest())
    report=dict(status='running',doi=DOI,author_commit=COMMIT,python=platform.python_version(),
        pair_worlds=0,evolution_worlds=0,decisions=0,actual_model_api_calls=0,recorded_cost_usd=0,
        compatibility='Action scalars normalized to Python int before history storage; restores NumPy 1.24 string-key behavior under NumPy 2.',
        source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
        comparisons=dict(pair_states_exact=True,pair_payoffs_exact=True,evolution_population_states_exact=True,evolution_payoff_atol=1e-12),
        scope='Author-trained strategy evaluation and reduced Fermi population dynamics; not retraining, full published sweep or human fidelity.')
    started=time.perf_counter();pairs=[];matrix_rows=defaultdict(list);evolution_rows=[];figure1={}
    try:
        for a,b,initial,seed in itertools.product(strategy_ids,strategy_ids,flags,seeds):
            w=RepeatedGame((a,b),initial,rounds,seed)
            result=run_simulation(w,AuthorStrategyEngine(w),rounds=rounds,seed=seed,output=root/'pairs'/f'p{len(pairs):04d}')
            reference=direct_reference((a,b),initial,rounds,seed)
            if [m['state_sha256'] for m in result['metrics']]!=[digest(s) for s in reference]:raise AssertionError('Source interaction trajectory differs.')
            matrix_rows[(a,b)].append((w.scores[0]/rounds,sum(1-row[0] for row in w.actions)/rounds))
            pairs.append(dict(a=NAMES[a],b=NAMES[b],flag0=initial[0],flag1=initial[1],seed=seed,
                rounds=rounds,payoff0=w.scores[0]/rounds,payoff1=w.scores[1]/rounds,cooperation=result['metrics'][-1]['cooperation'],
                state_sha256=digest(w.snapshot())))
            if a==b and a in (-1,0,6) and initial in ([0,1],[1,1]) and seed==seeds[0]:
                figure1[NAMES[a]+'_'+''.join(map(str,initial))]=w.actions
            report['pair_worlds']+=1;report['decisions']+=result['decisions']
        table=np.array([[mean(v[0] for v in matrix_rows[(a,b)]) for b in strategy_ids] for a in strategy_ids])
        coop=np.array([[mean(v[1] for v in matrix_rows[(a,b)]) for b in strategy_ids] for a in strategy_ids])
        save(root/'payoff_table.json',dict(strategies=[NAMES[s] for s in strategy_ids],payoffs=table.tolist(),cooperation=coop.tolist(),
            scope='Estimated from this reduced source-strategy tournament, not the paper\'s full Monte Carlo payoff matrix.'))
        for with_mtbr,selection,seed in itertools.product(ec['with_mtbr'],ec['selection'],seeds):
            w=WellMixedEvolution(table,coop,strategy_ids,agents=ec['agents'],rounds=ec['rounds'],selection=selection,seed=seed,with_mtbr=with_mtbr)
            reference=evolution_reference(w)
            result=run_staged_simulation(w,NativeImitation(w),rounds=w.rounds,seed=seed,output=root/'evolution'/f'e{len(evolution_rows):03d}')
            for metric,ref in zip(result['metrics'],reference):
                if metric['state_sha256']!=digest(ref['types']):raise AssertionError('Source sequential population refresh differs.')
                if abs(metric['mean_payoff']-mean(ref['fitness']))>1e-12:raise AssertionError('Source payoffs differ.')
                if abs(metric['mean_cooperation']-mean(ref['cooperation']))>1e-12:raise AssertionError('Source cooperation differs.')
            row=dict(with_mtbr=with_mtbr,selection=selection,seed=seed,agents=w.n,rounds=w.rounds,
                     initial_counts={NAMES[s]:w.initial.count(i) for i,s in enumerate(strategy_ids)},metrics=result['metrics'])
            evolution_rows.append(row);report['evolution_worlds']+=1;report['decisions']+=result['decisions']
        save(root/'figure1_trajectories.json',figure1);save(root/'evolution_trajectories.json',evolution_rows)
        with (root/'pair_summary.csv').open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(pairs[0]));writer.writeheader();writer.writerows(pairs)
        with (root/'evolution_summary.csv').open('w',encoding='utf-8',newline='') as stream:
            writer=csv.writer(stream);writer.writerow(['with_mtbr','selection','seed','generation','MTBR_share','mean_payoff','mean_cooperation'])
            for row in evolution_rows:
                for m in row['metrics']:writer.writerow([row['with_mtbr'],row['selection'],row['seed'],m['round'],m['counts']['MTBR']/row['agents'],m['mean_payoff'],m['mean_cooperation']])
        report['figure1_cases']=figure1;report['payoff_table']=table.tolist();report['strategies']=[NAMES[s] for s in strategy_ids]
        report['evolution_final']=[{k:v for k,v in r.items() if k!='metrics'}|{'final':r['metrics'][-1]} for r in evolution_rows]
        report['status']='complete'
    except Exception as error:report.update(status='failed',error_type=type(error).__name__);raise
    finally:report['elapsed_s']=time.perf_counter()-started;save(root/'verification.json',report)
    print(json.dumps({k:report[k] for k in ['status','pair_worlds','evolution_worlds','decisions','actual_model_api_calls','elapsed_s','comparisons']},indent=2),flush=True)


if __name__=='__main__':main()
