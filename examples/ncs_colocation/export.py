"""Export the co-location cookbook's compact, shareable results and figure."""
import argparse
import csv
import json
from pathlib import Path
import shutil
import statistics


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True)
    parser.add_argument('--output',default='docs/ncs_colocation/results')
    args=parser.parse_args();root=Path(args.run);out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    report=json.loads((root/'verification.json').read_text(encoding='utf-8'))
    if report['status']!='complete':raise ValueError('Export requires a completed audit.')
    for name in ['verification.json','summary.csv','trajectories.csv']:
        shutil.copyfile(root/name,out/name)
    rows=list(csv.DictReader((root/'trajectories.csv').open(encoding='utf-8')))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    populations=report['plan']['populations'];policies=report['plan']['policies']
    fig,axes=plt.subplots(1,len(populations),figsize=(11,4.1),squeeze=False)
    for ax,n in zip(axes[0],populations):
        for policy in policies:
            selected=[r for r in rows if int(r['population'])==n and r['policy']==policy]
            means=[];lower=[];upper=[]
            for t in range(1,sum(report['plan']['phase_days'])+1):
                values=[float(r['weak_ties']) for r in selected if int(r['round'])==t]
                means.append(statistics.mean(values));lower.append(min(values));upper.append(max(values))
            line=ax.plot(range(1,len(means)+1),means,label=policy.replace('_',' '))[0]
            ax.fill_between(range(1,len(means)+1),lower,upper,alpha=.13,color=line.get_color())
        first,second,_=report['plan']['phase_days']
        ax.axvline(first+.5,color='gray',linestyle='--',linewidth=1)
        ax.axvline(first+second+.5,color='gray',linestyle='--',linewidth=1)
        ax.set(title=f'Public demo: {n} nodes',xlabel='Native simulation day',ylabel='Weak ties (local bridges)')
        ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8,loc='lower left')
    fig.suptitle('Author network kernel through ORDO: co-location policy comparison',fontsize=12)
    fig.text(.5,.015,'Mean and min–max range over three seeds. Public demo, shortened horizon; no empirical effect-size claim.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.055,1,.95))
    fig.savefig(out/'colocation_policy.png',dpi=180);fig.savefig(out/'colocation_policy.pdf');plt.close(fig)
    groups=[]
    for n in populations:
        for policy in policies:
            subset=[w for w in report['worlds'] if w['population']==n and w['policy']==policy]
            groups.append(dict(population=n,policy=policy,seeds=len(subset),
                               phase_weak_ties=[statistics.mean(w[f'phase{k}_weak_ties_mean'] for w in subset) for k in range(3)]))
    (out/'group_summary.json').write_text(json.dumps(groups,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(output=str(out),worlds=len(report['worlds']),groups=groups)))


if __name__=='__main__':main()
