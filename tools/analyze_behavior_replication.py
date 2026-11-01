"""Summarize a complete fresh behavioral run; make standalone scientific figures.

python tools/analyze_behavior_replication.py --run runs/behavior-jev-20261029
"""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import mean,median
import sys


def wilson(k,n):
    z=1.959963984540054; p=k/n; d=1+z*z/n
    center=(p+z*z/(2*n))/d
    radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [0 if k==0 else max(0,center-radius),1 if k==n else min(1,center+radius)]


def final_flip(row):
    last=row['last']
    return last['window_interactions']>=72 and last['success']>=.95 and last['mutable_target_share'] is not None and last['mutable_target_share']>=.95


def summarize(group,rows):
    buckets=defaultdict(list)
    for row in rows: buckets[row['condition']].append(row)
    summary={}
    for condition,worlds in buckets.items():
        n=len(worlds)
        if group=='opinion':
            successes=sum(row['stop']=='consensus' for row in worlds)
            times=[row['first_consensus_update']/row['environment']['agents'] for row in worlds if row['stop']=='consensus']
            result=dict(worlds=n,consensus=successes,consensus_rate=successes/n,consensus_wilson95=wilson(successes,n),
                mean_final_coordination=mean(row['last']['coordination'] for row in worlds),
                median_time_among_consensus=median(times) if times else None)
        elif condition.startswith('spontaneous'):
            successes=sum(row['stop']=='spontaneous_convention' for row in worlds)
            times=[row['first_consensus_update']/24 for row in worlds if row['stop']=='spontaneous_convention']
            result=dict(worlds=n,conventions=successes,convention_rate=successes/n,convention_wilson95=wilson(successes,n),
                mean_final_success=mean(row['last']['success'] for row in worlds),
                mean_final_dominant_share=mean(row['last']['dominant_share'] for row in worlds),
                median_time_among_converged=median(times) if times else None,
                final_names=[row['last']['dominant'] for row in worlds])
        else:
            flips=sum(final_flip(row) for row in worlds)
            result=dict(worlds=n,first_target_windows=sum(row['first_target_window_update'] is not None for row in worlds),
                final_target_windows=flips,final_target_rate=flips/n,final_target_wilson95=wilson(flips,n),
                mean_final_success=mean(row['last']['success'] for row in worlds),
                mean_final_mutable_target_share=mean(row['last']['mutable_target_share'] for row in worlds))
        summary[condition]=result
    return summary


def trajectories(root,group,engine):
    data=defaultdict(list)
    with (root/f'{group}-{engine}'/'events.jsonl').open(encoding='utf-8') as stream:
        for line in stream:
            event=json.loads(line)
            for wid,row in event['metrics']['worlds'].items(): data[wid].append(row)
    return data


def audit_saved_probabilities(root,report):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from orgabm.sdk import run_simulation
    from examples.llm_abm_cookbook.behavior import make_naming_worlds,make_opinion_worlds
    for name,expected in report['source_hashes'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Experiment source changed since execution; preserve and use the recorded version for replay.')
    results={}
    for group,factory in [('naming',make_naming_worlds),('opinion',make_opinion_worlds)]:
        original=json.loads((root/f'{group}-jev'/'result.json').read_text(encoding='utf-8'))
        class Tape:
            def __init__(self,stream): self.stream=stream
            def decide(self,state,questions):
                row=json.loads(next(self.stream))
                if state!=row['state'] or questions!=row['questions']:
                    raise AssertionError('Reconstructed local input differs from the recorded input.')
                return row['probabilities']
            def usage(self): return dict(engine='saved-probability-replay',actual_model_api_calls=0)
        world=factory()
        with (root/f'{group}-jev'/'events.jsonl').open(encoding='utf-8') as stream:
            replay=run_simulation(world,Tape(stream),rounds=max(world.max_updates.values()),seed=717)
            if next(stream,None) is not None: raise AssertionError('Unconsumed recorded updates.')
        if replay['metrics']!=original['metrics']:
            raise AssertionError('Saved-probability replay metrics differ from the actual model run.')
        results[group]=dict(all_inputs_exact=True,all_metrics_exact=True,actual_model_api_calls=0,
                            decisions=replay['decisions'],ensemble_steps=replay['completed_rounds'])
    return results


def figures(root,out,report):
    extra=Path('.buildtmp/behavior-plot-deps')
    if extra.exists(): sys.path.insert(0,str(extra))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    colors={'jev':'#1666ad','uniform':'#a6a6a6'}
    trajectories_all={(group,engine):trajectories(root,group,engine)
                      for group in report['groups'] for engine in ['jev','uniform']}
    with (out/'trajectories.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream); writer.writerow(['group','engine','world','condition','update','population_time','success','dominant_share','mutable_target_share','coordination'])
        for (group,engine),data in trajectories_all.items():
            configs={r['world']:r for r in report['groups'][group][engine]['worlds']}
            for wid,series in data.items():
                for r in series:
                    writer.writerow([group,engine,wid,configs[wid]['condition'],r['updates'] if group=='naming' else r['update'],
                        r.get('population_rounds',r.get('population_time')),r.get('success'),r.get('dominant_share'),
                        r.get('mutable_target_share'),r.get('coordination')])

    def condition_lines(ax,group,condition,field,label,engine,style='-'):
        rows=[r for r in report['groups'][group][engine]['worlds'] if r['condition']==condition]
        horizon=1000 if group=='naming' else int(condition[1:])*10
        curves=[]
        for row in rows:
            series=trajectories_all[group,engine][row['world']]
            y=[r.get(field) for r in series]
            y=[float('nan') if value is None else value for value in y]
            curves.append(y+[y[-1]]*(horizon-len(y)))
        average=np.nanmean(np.array(curves),axis=0)
        n=24 if group=='naming' else int(condition[1:])
        ax.plot(np.arange(1,horizon+1)/n,average,style,label=label,color=colors[engine],lw=1.7)

    fig,axes=plt.subplots(1,3,figsize=(15,4.3),layout='constrained')
    for w,style in [(10,'-'),(2,'--')]:
        for engine in ['jev','uniform']:
            condition_lines(axes[0],'naming',f'spontaneous_W{w}','success',f'{engine}, W={w}',engine,style)
    axes[0].set(title='A  Spontaneous convention formation',xlabel='Pair interactions / N',ylabel='Success in last 3N pairs',ylim=(0,1.03))
    axes[0].legend(fontsize=8)
    for committed,color in [(0,'#777777'),(4,'#e69f00'),(5,'#009e73'),(8,'#cc3377')]:
        rows=[r for r in report['groups']['naming']['jev']['worlds'] if r['condition']==f'Q_to_M_{committed}']
        curves=[]
        for row in rows:
            values=[r['mutable_target_share'] for r in trajectories_all['naming','jev'][row['world']]]
            curves.append([float('nan') if x is None else x for x in values])
        axes[1].plot(np.arange(1,1001)/24,np.nanmean(np.array(curves),axis=0),color=color,label=f'{committed}/24 fixed M')
    axes[1].axhline(.95,c='black',ls=':',lw=1)
    axes[1].set(title='B  Adoption by non-fixed members',xlabel='Pair interactions / N',ylabel='M share in last 3N pairs',ylim=(0,1.03))
    axes[1].legend(fontsize=8)
    x=np.arange(4)
    for engine,offset in [('jev',-.18),('uniform',.18)]:
        stats=[report['summaries']['naming'][engine][f'Q_to_M_{k}'] for k in [0,4,5,8]]
        y=np.array([s['final_target_rate'] for s in stats]); ci=np.array([s['final_target_wilson95'] for s in stats])
        axes[2].bar(x+offset,y,.34,color=colors[engine],label=engine,yerr=[y-ci[:,0],ci[:,1]-y],capsize=3)
    axes[2].set(title='C  Final target-convention windows',xlabel='Fixed minority out of N=24',ylabel='Fraction of worlds; 95% Wilson CI',xticks=x,xticklabels=['0','4','5','8'],ylim=(0,1.1))
    axes[2].legend(fontsize=8)
    fig.suptitle('Fresh Jev substitution in published protocols | small predeclared replication',fontsize=12)
    fig.savefig(out/'naming_behavior.png',dpi=180); fig.savefig(out/'naming_behavior.pdf'); plt.close(fig)

    fig,axes=plt.subplots(1,3,figsize=(15,4.3),layout='constrained')
    for n,style in [(10,':'),(50,'-'),(100,'--')]:
        for engine in ['jev','uniform']:
            condition_lines(axes[0],'opinion',f'N{n}','coordination',f'{engine}, N={n}',engine,style)
    axes[0].set(title='A  Coordination dynamics',xlabel='Single-member updates / N',ylabel='Mean |m|',ylim=(0,1.03))
    axes[0].set_yticks([0,.2,.4,.6,.8,1],labels=['0.0','0.2','0.4','0.6','0.8','1.0'])
    axes[0].legend(fontsize=8,ncol=2)
    for engine,offset in [('jev',-.18),('uniform',.18)]:
        stats=[report['summaries']['opinion'][engine][f'N{n}'] for n in [10,50,100]]
        y=np.array([s['consensus_rate'] for s in stats]); ci=np.array([s['consensus_wilson95'] for s in stats])
        axes[1].bar(np.arange(3)+offset,y,.34,color=colors[engine],label=engine,yerr=[y-ci[:,0],ci[:,1]-y],capsize=3)
    axes[1].set(title='B  Consensus by population time 10',xlabel='Population size',ylabel='Fraction of worlds; 95% Wilson CI',xticks=np.arange(3),xticklabels=['10','50','100'],ylim=(0,1.1))
    axes[1].legend(fontsize=8)
    refs=report['author_opinion_reference']['models']
    names=['Jev (new)','Uniform (new)']+[r['file'].split('0.0_')[1].removesuffix('_MF.txt').replace('-20240307','').replace('-20240229','').replace('-2024-04-09','').replace('-1106','') for r in refs]
    values=[report['summaries']['opinion'][e]['N50']['mean_final_coordination'] for e in ['jev','uniform']]+[mean(abs(v) for v in r['values']) for r in refs]
    axes[2].barh(np.arange(len(names)),values,color=['#1666ad','#a6a6a6']+['#d6e5ef']*len(refs))
    axes[2].set(yticks=np.arange(len(names)),yticklabels=names,xlabel='Mean final |m|, N=50',xlim=(0,1.1),title='C  Descriptive archival reference')
    axes[2].tick_params(axis='y',labelsize=7); axes[2].invert_yaxis()
    fig.suptitle('Jev: fresh probabilities at every update | archived references are not matched new calls',fontsize=12)
    fig.savefig(out/'opinion_behavior.png',dpi=180); fig.savefig(out/'opinion_behavior.pdf'); plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True)
    parser.add_argument('--output',default='docs/llm_abm_cookbook/behavior_results')
    args=parser.parse_args(); root=Path(args.run); out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    report=json.loads((root/'verification.json').read_text(encoding='utf-8'))
    if report['status']!='complete' or set(report['groups'])!={'naming','opinion'}:
        raise ValueError('A complete two-protocol run is required; do not summarize partial runs as completed evidence.')
    report['summaries']={group:{engine:summarize(group,content['worlds']) for engine,content in results.items()}
                         for group,results in report['groups'].items()}
    report['offline_saved_probability_replay']=audit_saved_probabilities(root,report)
    report['source_hashes']={str(Path(k).resolve().relative_to(Path.cwd().resolve())).replace('\\','/'):v
                             for k,v in report['source_hashes'].items()}
    report['author_opinion_reference']=json.loads(Path('docs/llm_abm_cookbook/author_opinion_reference.json').read_text(encoding='utf-8'))
    report['frozen_plan']=json.loads((root/'plan-before-calls.json').read_text(encoding='utf-8'))
    report['run_manifest_sha256']=hashlib.sha256((root/'verification.json').read_bytes()).hexdigest()
    report['analysis_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    save=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save(out/'behavior_results.json',report)
    figures(root,out,report)
    lines=['# Fresh Jev social-behavior replications','','2026-10-29. New worlds use typesafe/jev-1.14-20261014 with a fresh judgment for every relevant event.', '',
        'The protocol and sample sizes are frozen in plan-before-calls.json. Typed probabilities and declared sampling replace text answers; prompts are semantically adapted.','',
        '## Conventions and committed minorities','','| Condition | Engine | Worlds | Criterion reached | Final-window coordination | Ordinary-member M share |',
        '| --- | --- | ---: | ---: | ---: | ---: |']
    for condition in report['summaries']['naming']['jev']:
        for engine in ['jev','uniform']:
            s=report['summaries']['naming'][engine][condition]
            achieved=s.get('conventions',s.get('final_target_windows'))
            lines.append(f"| {condition} | {engine} | {s['worlds']} | {achieved} | {s['mean_final_success']:.3f} | {s.get('mean_final_mutable_target_share','—') if 'mean_final_mutable_target_share' not in s else format(s['mean_final_mutable_target_share'],'.3f')} |")
    lines+=['','Spontaneous worlds stop after 72 consecutive matching pairs and at least 95% same-name actions, or at 1,000 pairs. Minority worlds start with five Q/Q histories and run 1,000 pairs; committed members always choose M. Minority criteria require at least 95% matching pairs and ordinary-member M actions in the final 72-pair window. First qualifying windows are also recorded.','',
        '![Conventions and minority intervention](naming_behavior.png)','','## Group coordination','','| Population | Engine | Worlds | Consensus by t=10 | Mean final coordination |',
        '| ---: | --- | ---: | ---: | ---: |']
    for condition in report['summaries']['opinion']['jev']:
        for engine in ['jev','uniform']:
            s=report['summaries']['opinion'][engine][condition]
            lines.append(f"| {condition[1:]} | {engine} | {s['worlds']} | {s['consensus']} | {s['mean_final_coordination']:.3f} |")
    lines+=['','Balanced initial opinions update one random member at a time until consensus or t=10. Consensus endpoints are extended for plotting without new calls. Intervals use independent worlds.','',
        '![Group coordination](opinion_behavior.png)','','## Author-data comparison','',
        'The N=50 reference bars use archived author endpoint files with 20–28 records per model. Actual file counts are retained. These are descriptive archived comparisons rather than newly executed source-model arms.','',
        'The selected conditions cover convention emergence and coordination. Bidirectional minority thresholds, splitting trees and full critical-size curves remain outside this run. Categorical probability sampling and argmax are distinct behavioral policies. Uniform choice provides a chance baseline.','',
        'Saved-probability replay exactly reconstructs all local inputs and step metrics for both protocols, without model requests.','',
        f"Returned input usage is {report['usage']['input_tokens']:,} tokens across {report['usage']['successful_responses']:,} successful requests, with provider-reported cost **${report['usage']['recorded_input_cost_usd']:.6f}**.",'',
        '[Machine-readable results and plans](behavior_results.json); [world trajectories](trajectories.csv). PNG figures also have PDF versions. Full request and action records remain in the run directory.','']
    if 'recovery' in report:
        lines+=['## Execution and recovery','',
            f"A network request returned no response after {report['recovery']['completed_prefix_steps']} completed opinion steps. Recovery reconstructs historical inputs and requests only remaining decisions; original records are retained.",'',
            f"There are {report['usage'].get('ambiguous_prior_failed_requests',0)} requests without confirmed responses. Reported cost sums successful usage.cost; elapsed time includes a pause and recovery.",'']
    (out/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(report['summaries'],indent=2))


if __name__=='__main__': main()
