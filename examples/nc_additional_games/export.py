"""Export NC native social-rewarding evidence, trajectories and figure."""
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
    p.add_argument('--output',default='docs/nc_additional_games/results');args=p.parse_args()
    root=Path(args.run);out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    report=json.loads((root/'verification.json').read_text(encoding='utf-8'))
    if report['status']!='complete':raise ValueError('Require complete experimental evidence.')
    portable={}
    for name,sha in report['source_hashes'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=sha:raise ValueError('Experiment source changed.')
        portable[Path(name).resolve().relative_to(Path.cwd()).as_posix()]=sha
    report['source_hashes']=portable;report['analysis_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for f in ['sources.json','plan.json','trajectories.csv']:shutil.copyfile(root/f,out/f)
    (out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    groups=defaultdict(list)
    for w in report['worlds']:groups[(w['config']['information'],w['config']['mutation'])].append(w)
    with (out/'world_summary.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['information','mutation','seed','updates','final_cooperation','last_third_cooperation','last_third_social_rewarding'])
        for w in report['worlds']:
            c=w['config'];writer.writerow([c['information'],c['mutation'],c['seed'],c['rounds'],w['final']['post_cooperation'],
                w['last_third_mean_cooperation'],w['last_third_mean_social_rewarding']])
    extra=Path('.buildtmp/behavior-plot-deps')
    if extra.exists():sys.path.insert(0,str(extra))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    data=defaultdict(list)
    with (root/'trajectories.csv').open(encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            if int(row['update'])%10==0:data[int(row['world'])].append([int(row['update']),float(row['cooperation']),float(row['social_rewarding_share'])])
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    mus=sorted({key[1] for key in groups});colors={0:'#777777',.5:'#009e73',1:'#1666ad'}
    for col,mu in enumerate(mus):
        for information in sorted({key[0] for key in groups}):
            rows=groups[(information,mu)]
            array=np.array([data[w['world']] for w in rows])
            for row,metric in enumerate((1,2)):
                values=array[:,:,metric];xs=array[0,:,0]
                axes[row,col].plot(xs,values.mean(axis=0),color=colors[information],label=f'information={information:g}')
                axes[row,col].fill_between(xs,values.min(axis=0),values.max(axis=0),color=colors[information],alpha=.1)
        axes[0,col].set(title=f'Mutation rate {mu:g}',ylabel='Expected cooperation',ylim=(0,1))
        axes[1,col].set(xlabel='Single-member strategy update',ylabel='Social rewarding strategy share',ylim=(0,1))
    axes[0,1].legend(fontsize=8)
    fig.suptitle('NC social-rewarding source-rule simulation | 100 members; 3 seeds; shading=min–max')
    for extension in ('png','pdf'):fig.savefig(out/f'social_rewarding.{extension}',dpi=180)
    plt.close(fig)
    lines=['# Reputation and social rewards: native results','',
        '[Pal & Hilbe (2022), Nature Communications 13:5928](https://doi.org/10.1038/s41467-022-33551-y). The pinned MIT source kernel runs through Environment/DecisionEngine.','',
        f"Completed **{len(report['worlds'])} worlds** of 100 members and 3,000 strategy updates, totaling **{report['decisions']:,} native choices**, zero APIs and zero model charges. Runtime including reference checks and logs is {report['elapsed_s']:.2f} seconds.",'',
        '## Results','',
        'Members combine donation strategies C/OC/OD/D with reward strategies NR/SR/AR/UR. Mutation and payoff-based Fermi imitation update the 16 combinations. Lambda is the probability that a donor observes the recipient reward policy. Values average the final third of updates and then three seeds.','',
        '| Information visibility | Mutation rate | Cooperation | Social-reward share |','| ---: | ---: | ---: | ---: |']
    for key,rows in sorted(groups.items()):
        lines.append(f"| {key[0]:g} | {key[1]:g} | {mean(w['last_third_mean_cooperation'] for w in rows):.1%} | {mean(w['last_third_mean_social_rewarding'] for w in rows):.1%} |")
    lines+=['','![Social rewards](social_rewarding.png)','',
        'The finite-horizon grid retains all condition outcomes and their variation.','',
        '## Verification','',
        'Every individual strategy, population count and pre/post-update cooperation metric matches an independent source loop. Native analytical payoffs and mutation/imitation are retained.','',
        'Three declared seeds replace the unseeded source script. Source CSV records before updates; this adapter retains both pre- and post-update states. Initialization matches the source.','',
        'Python 3.11 requires converting the sampled set to a list. The loader compiles pinned source functions and the update body while excluding top-level scans, prints and file writes.','',
        'The paper uses up to 10^9 updates for steady-state estimates. This run checks source-kernel equivalence over the declared finite horizon.','',
        '[Methods](../README.md) · [Verification](verification.json) · [Sources](sources.json) · [Worlds](world_summary.csv) · [Trajectories](trajectories.csv)','']
    (out/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(status='exported',output=str(out),frozen_sources_exact=True)))


if __name__=='__main__':main()
