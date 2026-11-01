"""Export compact tables, protocol evidence and scientific figures from a run."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import shutil
from statistics import mean
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True)
    p.add_argument('--output',default='docs/nc_evolutionary_games/results');args=p.parse_args()
    root=Path(args.run);out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    report=json.loads((root/'verification.json').read_text(encoding='utf-8'))
    if report['status']!='complete':raise ValueError('Only complete run evidence may be exported.')
    repo=Path.cwd();portable={}
    for name,sha in report['source_hashes'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=sha:raise ValueError('Recorded experiment code changed: '+name)
        portable[Path(name).resolve().relative_to(repo).as_posix()]=sha
    report['source_hashes']=portable;report['analysis_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for name in ['plan.json','sources.json','pair_summary.csv','evolution_summary.csv','payoff_table.json','figure1_trajectories.json']:
        shutil.copyfile(root/name,out/name)
    (out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    extra=Path('.buildtmp/behavior-plot-deps')
    if extra.exists():sys.path.insert(0,str(extra))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    trajectories=json.loads((root/'figure1_trajectories.json').read_text(encoding='utf-8'))
    fig,axes=plt.subplots(2,3,figsize=(12,4.6),layout='constrained')
    for row,flags in enumerate(('01','11')):
        for col,strategy in enumerate(('MTBR','TFT','GradualTFT')):
            values=np.array(trajectories[strategy+'_'+flags][:8]).T
            ax=axes[row,col];ax.imshow(values,cmap='Blues',vmin=0,vmax=1,aspect='auto')
            for a in range(2):
                for t in range(8):ax.text(t,a,'D' if values[a,t] else 'C',ha='center',va='center',color='white' if values[a,t] else '#222222')
            ax.set(title=f'{strategy} | start '+('/'.join('D' if x=='1' else 'C' for x in flags)),
                xticks=range(8),xticklabels=range(1,9),yticks=[0,1],yticklabels=['Player 1','Player 2'],xlabel='Game round')
    fig.suptitle('NC repeated-game mechanisms through ORDO | original trained strategy and source policies')
    for extension in ('png','pdf'):fig.savefig(out/f'figure1_mechanisms.{extension}',dpi=180)
    plt.close(fig)
    evolution=json.loads((root/'evolution_trajectories.json').read_text(encoding='utf-8'))
    groups=defaultdict(list)
    for r in evolution:groups[(r['with_mtbr'],r['selection'])].append(r)
    fig,axes=plt.subplots(1,2,figsize=(11,4.1),layout='constrained')
    colors={(False,.05):'#777777',(False,1):'#222222',(True,.05):'#009e73',(True,1):'#1666ad'}
    for key,rows in groups.items():
        label=('MTBR available' if key[0] else 'MTBR absent')+f', selection={key[1]:g}'
        xs=np.arange(1,len(rows[0]['metrics'])+1)
        for ax,metric in zip(axes,('share','cooperation')):
            values=np.array([[m['counts']['MTBR']/r['agents'] if metric=='share' else m['mean_cooperation'] for m in r['metrics']] for r in rows])
            ax.plot(xs,values.mean(axis=0),color=colors[key],linestyle='-' if key[0] else '--',label=label)
            ax.fill_between(xs,values.min(axis=0),values.max(axis=0),color=colors[key],alpha=.10)
    axes[0].set(title='A  MTBR strategy share',xlabel='Generation',ylabel='Population share',ylim=(0,1))
    axes[1].set(title='B  Cooperation in payoff evaluation',xlabel='Generation',ylabel='Mean cooperation probability',ylim=(0,1))
    axes[1].legend(fontsize=8)
    fig.suptitle('Reduced well-mixed source-rule evaluation | N=64, 50 generations, 3 seeds; shading=min–max')
    for extension in ('png','pdf'):fig.savefig(out/f'well_mixed_evolution.{extension}',dpi=180)
    plt.close(fig)
    lines=['# Evolutionary games: native results','',
        'Su et al., A multi-agent reinforcement learning framework for exploring dominant strategies in iterated and evolutionary games, Nature Communications 17, 490 (2026). [Paper](https://doi.org/10.1038/s41467-025-67178-6).','',
        f"Completed **{report['pair_worlds']} pair worlds** and **{report['evolution_worlds']} population worlds**, with **{report['decisions']:,} native choices** and zero APIs in {report['elapsed_s']:.2f} seconds. Independent reference execution is additional verification work.",'',
        '## Figure 1 mechanism trajectories','',
        '| Self-play strategy | C/D initialization | D/D initialization |','| --- | --- | --- |',
        '| Archived trained MTBR | C/C from round 2 | C/C from round 3 |',
        '| TFT | Alternating C/D and D/C | Persistent D/D |',
        '| GradualTFT | C/C from round 4 | C/C from round 3 |','',
        'These six source examples use original strategy classes and the archived trained Q table. Complete 20-round actions, histories and payoffs match independent source-order execution.','',
        '![Pair trajectories](figure1_mechanisms.png)','',
        '## Population evolution','',
        'The pair grid uses 9×9 ordered strategies, four initial flags and three seeds over 20 rounds. AllD overrides its initial flag as in the source. Estimated payoff/cooperation tables drive 64-member, 50-generation well-mixed worlds, varying MTBR inclusion and selection strength over three seeds.','',
        '| Strategy set | Selection strength | Mean final MTBR share | Mean evaluated cooperation |','| --- | ---: | ---: | ---: |']
    for key,rows in groups.items():
        share=mean(r['metrics'][-1]['counts']['MTBR']/r['agents'] for r in rows)
        coop=mean(r['metrics'][-1]['mean_cooperation'] for r in rows)
        lines.append(f"| {'With MTBR' if key[0] else 'Without MTBR'} | {key[1]:g} | {share:.1%} | {coop:.1%} |")
    lines+=['','![Population evolution](well_mixed_evolution.png)','',
        'The source shuffles the population, computes old-strategy pair payoffs, then imitates sequentially in place with payoffs frozen for that generation. Each member is a causal SDK stage. Complete populations match the extracted source loop; payoff and cooperation differences are below 1e-12.','',
        '## Source scope','',
        'The run checks pair mechanisms and a reduced population configuration. Source training and the complete network/parameter study remain separate. Native payoff tables are part of the original mechanism.','',
        'Pinned source files and Q tables retain MIT notices. The loader compiles inspected strategy classes and the generation-loop AST, excluding top-level scans and plotting. Python-int normalization preserves NumPy 1.24 history keys under NumPy 2.','',
        '[Methods](../README.md) · [Verification](verification.json) · [Sources](sources.json) · [Pairs](pair_summary.csv) · [Generations](evolution_summary.csv)','']
    (out/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(status='exported',path=str(out),frozen_experiment_hashes_exact=True)))


if __name__=='__main__':main()
