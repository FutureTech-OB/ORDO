"""Export author-code foraging parity and observed native trajectories."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
from statistics import mean
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True)
    p.add_argument('--output',default='docs/nc_social_sweep/foraging_results');a=p.parse_args()
    root=Path(a.run);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    report=json.loads((root/'verification.json').read_text(encoding='utf-8'))
    if report['status']!='complete':raise ValueError('Preserve incomplete runs separately.')
    for name,sha in report['source_hashes'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=sha:raise ValueError('Run sources changed.')
    report['source_hashes']={Path(f).resolve().relative_to(Path.cwd().resolve()).as_posix():sha for f,sha in report['source_hashes'].items()}
    curves={};groups=defaultdict(list)
    with (out/'trajectories.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['world','environment','policy','seed','step','cumulative_group_reward','revealed_blocks'])
        for row in report['worlds']:
            stats=json.loads((root/f"world-{row['world']:03d}"/'step_statistics.json').read_text(encoding='utf-8'))
            step_groups=defaultdict(list)
            for s in stats:step_groups[s['step']].append(s)
            cumulative=0;curve=[]
            for step,observations in step_groups.items():
                cumulative+=sum(int(x['reward']) for x in observations);curve.append(cumulative)
                writer.writerow([row['world'],row['environment'],row['policy'],row['seed'],step,cumulative,observations[0]['revealed']])
            curves[row['world']]=curve;groups[(row['environment'],row['policy'])].append(row)
    (out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'summary.csv').write_bytes((root/'summary.csv').read_bytes())
    extra=Path('.buildtmp/behavior-plot-deps')
    if extra.exists():sys.path.insert(0,str(extra))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    colors={'asocial':'#666666','unbiased_social':'#009e73','success_biased_social':'#cc3377'}
    fig,axes=plt.subplots(1,2,figsize=(10,3.8),layout='constrained')
    for ax,env in zip(axes,['smooth','random']):
        for policy,color in colors.items():
            rows=groups[(env,policy)];array=np.array([curves[r['world']] for r in rows]);steps=np.arange(array.shape[1])
            ax.plot(steps,array.mean(axis=0),label=policy,color=color)
            ax.fill_between(steps,array.min(axis=0),array.max(axis=0),color=color,alpha=.1)
        ax.set(title=env+' reward map',xlabel='Original physical timestep',ylabel='Cumulative group reward');ax.legend(fontsize=8)
    fig.suptitle('Unmodified author foraging mechanics | 4 agents; 3 seeds per strategy; two selected published maps')
    fig.savefig(out/'foraging.png',dpi=180);fig.savefig(out/'foraging.pdf');plt.close(fig)
    lines=['# Collective foraging through ORDO','','[Adaptive mechanisms of social and asocial learning in immersive collective foraging](https://doi.org/10.1038/s41467-025-58365-6), Nature Communications (2025).','',
        f"Completed {len(report['worlds'])} worlds with four members and 400 physical steps each, producing {report['decisions']:,} target choices. Two source maps and three native policies use three seeds per condition, with zero APIs.",'',
        'Every physical state, private AgentView, navigation, collection and individual statistic matches the original Simulation.run. Saved-choice replay also matches local inputs and metrics.','',
        '| Map | Native policy | Mean group reward | Mean revealed resource cells |','| --- | --- | ---: | ---: |']
    for (env,policy),rows in groups.items():lines.append(f"| {env} | {policy} | {mean(x['total_rewards'] for x in rows):.1f} | {mean(x['revealed_blocks'] for x in rows):.1f} |")
    lines+=['','![Native foraging](foraging.png)','','Lines show three-seed means and shading the observed range. The declared suite uses two source maps.','',
        'Only goal_cell = policy.sample_next_cell(...) becomes a yield boundary for ORDO to record a native choice before resuming the source loop. State, AgentView, Policy, Gaussian process, visibility, navigation and collection retain source semantics. Native PCG64 choices are recorded as one-hot actions.','',
        'An SDK round is a target choice, distinct from a physical timestep. The bound is 4×400=1,600 stages per world; empty post-completion stages produce no choices. Charts use physical time.','',
        '[Methods and notices](../foraging.md) · [Verification](verification.json) · [Worlds](summary.csv) · [Physical trajectories](trajectories.csv)','']
    (out/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(status='complete',worlds=len(report['worlds']),decisions=report['decisions'],actual_api_calls=0),indent=2))


if __name__=='__main__':main()
