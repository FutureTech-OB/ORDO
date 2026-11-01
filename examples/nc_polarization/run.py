"""Replay NC polarization source states/networks and check curated figure counts."""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import time

import numpy as np

from orgabm.sdk import run_simulation
from .archive import load_snapshot,metrics
from .model import PolarizationSnapshots,RecordedStateEngine,digest
from .sources import load_sources

TOPICS=['Partisan Alignment','Gun Control','Abortion Ban']


def save(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def reference_metrics(snapshot):
    values=np.asarray(snapshot['states'],dtype=int);edge=np.asarray(snapshot['edges'],dtype=int)
    count=np.bincount(values+2,minlength=5)
    return dict(counts={str(i-2):int(c) for i,c in enumerate(count)},neutral_share=float(np.mean(values==0)),
        mean_opinion=float(np.mean(values)),polarization=float(np.abs(values).mean()),
        exact_opinion_homophily=float(np.mean(values[edge[:,0]]==values[edge[:,1]])),
        same_sign_homophily=float(np.mean(np.sign(values[edge[:,0]])==np.sign(values[edge[:,1]]))))


def figure_lookup(root):
    result={}
    for label,file in [('baseline','figures/figure1/data/figure1_node_state_proportions.csv'),
                       ('debiased','figures/figure2/data/figure2d_debiased_node_state_proportions.csv')]:
        with (root/file).open(encoding='utf-8') as stream:rows=list(csv.DictReader(stream))
        result[label]={(r['topic_title'],int(r['epoch']),int(r['state'])):int(r['count']) for r in rows}
    return result


def export_plot(out,rows):
    import sys
    extra=Path('.buildtmp/behavior-plot-deps')
    if extra.exists():sys.path.insert(0,str(extra))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(12.5,3.7),layout='constrained')
    for topic in TOPICS:
        r=[x for x in rows if x['topic']==topic]
        for ax,key,title in zip(axes,['neutral_share','polarization','same_sign_homophily'],
            ['Neutral opinions','Mean absolute opinion','Same-sign directed contacts']):
            ax.plot([x['epoch'] for x in r],[x[key] for x in r],label=topic)
            ax.set(xlabel='Archived epoch',title=title)
            ax.spines[['top','right']].set_visible(False)
    axes[0].set_ylabel('Share');axes[1].set_ylabel('Mean |opinion|');axes[2].set_ylabel('Share of edge rows')
    axes[0].legend(fontsize=8)
    fig.suptitle('NC polarization: 1,000 members per topic | archived state/network replay, no fresh inference',fontsize=10)
    fig.savefig(out/'polarization_archive.png',dpi=180);fig.savefig(out/'polarization_archive.pdf');plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',default='.buildtmp/nc-polarization-sources')
    p.add_argument('--download',action='store_true');p.add_argument('--output',required=True)
    p.add_argument('--export',default='docs/nc_polarization/results')
    args=p.parse_args();root=Path(args.cache);out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter();sources=load_sources(root,args.download);save(out/'source_manifest.json',sources)
    figures=figure_lookup(root)
    with (root/'source_data/metadata.csv').open(encoding='utf-8') as stream:
        metadata={(r['folder'],int(r['epoch'])):r for r in csv.DictReader(stream)}
    report=dict(status='running',source_commit=sources['commit'],doi=sources['doi'],topics={},actual_model_api_calls=0,
        evidence='state/network archive replay; no missing messages or original model probabilities reconstructed',
        source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
        metadata_discrepancies=[])
    rows=[];payload={}
    for topic in TOPICS:
        snapshots=[load_snapshot(root/'source_data'/topic/f'epoch_run{t}.pkl') for t in range(41)]
        payload[topic]=snapshots;w=PolarizationSnapshots(topic,snapshots)
        r=run_simulation(w,RecordedStateEngine(w),rounds=40,seed=7,output=out/topic.replace(' ','_'))
        assert r['status']=='complete' and len(w.trajectory)==41
        matches=Counter();duplicates=[];edge_rows=0
        for epoch,snapshot in enumerate(w.trajectory):
            if digest(snapshot)!=digest(snapshots[epoch]):raise AssertionError('Full opinions or topology differ from source.')
            m=metrics(snapshot);reference=reference_metrics(snapshots[epoch])
            for key,value in reference.items():
                if m[key]!=value:raise AssertionError('Independent source metric mismatch: '+key)
            for label,lookup in figures.items():
                if all(lookup.get((topic,epoch,int(state)))==count for state,count in m['counts'].items()):matches[label]+=1
            meta=metadata[(topic,epoch)]
            for key,actual in [('rows',m['edges']),('unique_edges',m['unique_edges'])]:
                if int(meta[key])!=actual:report['metadata_discrepancies'].append(dict(topic=topic,epoch=epoch,
                    field=key,reported=int(meta[key]),observed=actual))
            rows.append(dict(topic=topic,epoch=epoch,**m));edge_rows+=m['edges']
            if m['duplicate_edge_rows']:duplicates.append(dict(epoch=epoch,duplicate_edge_rows=m['duplicate_edge_rows']))
        matched=[label for label,n in matches.items() if n==41]
        if len(matched)!=1:raise AssertionError('Source archive could not be uniquely matched to one curated figure condition.')
        report['topics'][topic]=dict(population=1000,snapshots=41,periods=40,restored_member_states=r['decisions'],
            directed_edge_rows=edge_rows,curated_condition=matched[0],all_205_figure_counts_exact=True,
            all_states_and_edge_rows_exact=True,independent_metrics_exact=True,duplicate_edge_rows_preserved=duplicates,
            initial=metrics(snapshots[0]),final=metrics(snapshots[-1]),elapsed_s=r['elapsed_s'])
        print(json.dumps({topic:report['topics'][topic]}),flush=True)
    report.update(status='complete',elapsed_s=time.perf_counter()-started,
        total_snapshots=sum(r['snapshots'] for r in report['topics'].values()),
        total_restored_member_states=sum(r['restored_member_states'] for r in report['topics'].values()),
        total_directed_edge_rows=sum(r['directed_edge_rows'] for r in report['topics'].values()))
    save(out/'verification.json',report)
    exported=Path(args.export);exported.mkdir(parents=True,exist_ok=True)
    save(exported/'verification.json',report);save(exported/'source_manifest.json',sources)
    packed=json.dumps(payload,separators=(',',':')).encode();file=exported/'snapshots.json.gz'
    with gzip.GzipFile(filename='',mode='wb',fileobj=file.open('wb'),mtime=0) as stream:stream.write(packed)
    save(exported/'replay_manifest.json',dict(file=file.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
        sources_sha256=hashlib.sha256((exported/'source_manifest.json').read_bytes()).hexdigest()))
    with (exported/'trajectories.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=[k for k in rows[0] if k!='counts']);writer.writeheader()
        writer.writerows({k:v for k,v in row.items() if k!='counts'} for row in rows)
    shutil.copy2(root/'LICENSE',exported/'UPSTREAM_LICENSE.txt')
    export_plot(exported,rows)
    print(json.dumps({k:report[k] for k in ['status','total_snapshots','total_restored_member_states','total_directed_edge_rows','actual_model_api_calls']}))


if __name__=='__main__':main()
