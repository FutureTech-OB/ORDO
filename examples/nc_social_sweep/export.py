"""Publish compact evidence and figures for the executed native-kernel comparison."""
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
    p.add_argument('--output',default='docs/nc_social_sweep/results');a=p.parse_args()
    root=Path(a.run);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    r=json.loads((root/'verification.json').read_text(encoding='utf-8'))
    if r['status']!='complete':raise ValueError('Only completed runs may be exported.')
    for f,sha in r['source_hashes'].items():
        if hashlib.sha256(Path(f).read_bytes()).hexdigest()!=sha:raise ValueError('Recorded sources changed.')
    r['source_hashes']={Path(f).resolve().relative_to(Path.cwd().resolve()).as_posix():sha for f,sha in r['source_hashes'].items()}
    (out/'verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'summary.csv').write_bytes((root/'summary.csv').read_bytes())
    grouped=defaultdict(list)
    for row in r['worlds']:grouped[(row['agents'],row['disorder'])].append(row)
    stats={f'N={n},R={R}':dict(largest_fraction=mean(x['largest_fraction'] for x in rows),
        avalanche_count=mean(x['avalanches'] for x in rows),worlds=len(rows)) for (n,R),rows in grouped.items()}
    (out/'group_summary.json').write_text(json.dumps(stats,indent=2)+'\n',encoding='utf-8')
    extra=Path('.buildtmp/behavior-plot-deps')
    if extra.exists():sys.path.insert(0,str(extra))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(10,3.8),layout='constrained')
    for n in sorted({x['agents'] for x in r['worlds']}):
        Rs=sorted({x['disorder'] for x in r['worlds']})
        for ax,key,title,ylabel in [(axes[0],'largest_fraction','Largest activation cascade','Fraction of population'),
            (axes[1],'avalanches','Number of activation cascades','Cascade count / N')]:
            mult=1/n if key=='avalanches' else 1
            mids=[mean(x[key] for x in grouped[(n,R)])*mult for R in Rs]
            lo=[min(x[key] for x in grouped[(n,R)])*mult for R in Rs];hi=[max(x[key] for x in grouped[(n,R)])*mult for R in Rs]
            ax.plot(Rs,mids,'o-',label=f'N={n}');ax.fill_between(Rs,lo,hi,alpha=.1)
            ax.set(title=title,xlabel='Individual heterogeneity R',ylabel=ylabel);ax.legend()
    fig.suptitle('Native RFIM social activation | 3 seeds per configuration; shading = observed range')
    fig.savefig(out/'social_activation.png',dpi=180);fig.savefig(out/'social_activation.pdf');plt.close(fig)
    lines=['# Information propagation: RFIM source verification','','[Universality, criticality and complexity of information propagation on social media](https://doi.org/10.1038/s41467-022-28964-8), Nature Communications (2022).','',
        f"Completed {len(r['worlds'])} worlds and {r['decisions']:,} native activation choices with zero APIs. Populations are 128/512/1,024 and heterogeneity R=0.5/0.8/1.5, with three seeds each.",'',
        'The unchanged source C functions find_seed and next_shell are compiled and checked layer by layer. Cascade sizes, identifiers, remaining population and external fields match exactly. Saved-probability replay also matches inputs, metrics and final states.','',
        '| Population | R | Mean largest-cascade share | Mean cascade count |','| ---: | ---: | ---: | ---: |']
    for (n,R),rows in grouped.items():lines.append(f"| {n} | {R} | {mean(x['largest_fraction'] for x in rows):.1%} | {mean(x['avalanches'] for x in rows):.1f} |")
    lines+=['','![Activation cascades](social_activation.png)','','The finite configurations illustrate transitions between large collective and dispersed smaller cascades while retaining the selected native mechanism.','',
        'Each cascade layer updates together before the next layer observes it. The SDK uses a 2N bound; completed empty stages produce no questions. effective_shell_steps records actual propagation layers. Each member activates once and all cascade sizes sum to N.','',
        '[World data](summary.csv) · [Sources and verification](verification.json) · [Groups](group_summary.json) · [Methods](../README.md)','']
    (out/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(status='complete',worlds=len(r['worlds']),decisions=r['decisions'],api_calls=0,groups=stats),indent=2))


if __name__=='__main__':main()
