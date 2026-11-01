"""Plot saved organizational results; no API calls or image generation."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'docs/figures'


def main():
    source = ROOT/'docs/organizational_conventions/results/world_summary.csv'
    summary_path = ROOT/'docs/organizational_conventions/results/results.json'
    with source.open(encoding='utf-8', newline='') as stream:
        rows = [r for r in csv.DictReader(stream) if r['engine']=='jev']
    summaries = json.loads(summary_path.read_text(encoding='utf-8'))['summary']['jev']
    assert len(rows)==12
    data=[]
    for placement in ['employee','manager']:
        for mode in ['none','peer','official']:
            group=sorted((r for r in rows if r['placement']==placement and r['message_mode']==mode), key=lambda r:int(r['seed']))
            assert len(group)==2 and {int(r['seed']) for r in group}=={7,11}
            values=[float(r['voluntary_M_share']) for r in group]
            summary=summaries[placement+' / '+mode]
            mean=float(np.mean(values))
            assert abs(mean-summary['voluntary_M_share'])<1e-12
            data.append(dict(placement=placement,guidance=mode,seed_7=values[0],seed_11=values[1],mean=mean,
                             seeded_department_mean=summary['targeted_department_M_share'],
                             other_department_mean=summary['untargeted_department_M_share']))
    OUT.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,
                         'axes.spines.right':False,'axes.labelcolor':'#24384b','text.color':'#132b43',
                         'axes.edgecolor':'#a6b4bf','pdf.fonttype':42,'svg.fonttype':'none'})
    fig,axs=plt.subplots(1,2,figsize=(13.6,5.5),gridspec_kw={'width_ratios':[1.15,1]})
    fig.subplots_adjust(left=.065,right=.985,bottom=.24,top=.77,wspace=.28)
    fig.suptitle('Conventions in a 1,000-member organization',x=.065,ha='left',y=.98,fontsize=20,fontweight='bold')
    fig.text(.065,.907,'50 departments  |  20 committed members  |  32 periods  |  2 seeds per condition',fontsize=11,color='#53687b')
    ax=axs[0]; x=np.arange(3);width=.32
    for placement,color,offset,label in [('employee','#274d73',-width/2,'Committed employees'),('manager','#248d91',width/2,'Committed managers')]:
        group=[r for r in data if r['placement']==placement]
        means=[r['mean'] for r in group]
        centers=x+offset
        ax.bar(centers,means,width=width,color=color,label=label,zorder=2)
        for center,row in zip(centers,group):
            values=[row['seed_7'],row['seed_11']]
            ax.scatter([center-.042,center+.042],values,s=28,facecolor='white',edgecolor='#132b43',linewidth=.9,zorder=4)
            ax.text(center,max(values)+.012,f"{100*row['mean']:.1f}%",ha='center',va='bottom',fontsize=10,fontweight='bold')
    ax.set_title('A  Final adoption across guidance conditions',loc='left',fontweight='bold',fontsize=12,pad=17)
    ax.set_xticks(x,['No guidance','Peer guidance','Formal guidance'])
    ax.set_ylim(0,.32);ax.set_yticks([0,.1,.2,.3]);ax.yaxis.set_major_formatter(PercentFormatter(1,decimals=0))
    ax.set_ylabel('Ordinary members whose latest choice is M')
    ax.legend(loc='upper left',frameon=False,fontsize=9,ncol=2,handlelength=1.3,columnspacing=1)
    ax.grid(axis='y',color='#e2e9ee',linewidth=.7,zorder=0);ax.set_axisbelow(True)
    ax=axs[1]; x=np.arange(2);width=.3
    selected=[r for r in data if r['guidance']=='official']
    for key,color,offset,label in [('seeded_department_mean','#b78b36',-width/2,'Seeded departments'),('other_department_mean','#a8b7c4',width/2,'Other departments')]:
        values=[r[key] for r in selected]
        ax.bar(x+offset,values,width=width,color=color,label=label,zorder=2)
        for center,value in zip(x+offset,values):
            ax.text(center,value+.016,f'{100*value:.1f}%',ha='center',va='bottom',fontsize=10,fontweight='bold')
    ax.set_title('B  Department boundaries under formal guidance',loc='left',fontweight='bold',fontsize=12,pad=17)
    ax.set_xticks(x,['Employee placement','Manager placement'])
    ax.set_ylim(0,.76);ax.set_yticks([0,.2,.4,.6]);ax.yaxis.set_major_formatter(PercentFormatter(1,decimals=0))
    ax.set_ylabel('Ordinary members whose latest choice is M')
    ax.legend(loc='upper left',frameon=False,fontsize=9,ncol=2,handlelength=1.3,columnspacing=1)
    ax.grid(axis='y',color='#e2e9ee',linewidth=.7,zorder=0);ax.set_axisbelow(True)
    fig.text(.065,.11,'Bars show means across two seeds; open dots in A show individual seeds. Committed members are excluded.',fontsize=10,color='#53687b')
    fig.text(.065,.065,'Placement varies contact opportunities and organizational role context together.',fontsize=10,color='#53687b')
    for suffix in ['png','pdf','svg']:
        fig.savefig(OUT/f'ordo_organization_results_clean.{suffix}',dpi=260,facecolor='white',bbox_inches='tight')
    plt.close(fig)
    with (OUT/'ordo_organization_results_clean_data.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    (OUT/'ordo_organization_results_clean_provenance.json').write_text(json.dumps(dict(
        method='Matplotlib plot of saved experiment data; no generated numerical content',actual_model_api_calls=0,
        raw_csv_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        summary_json_sha256=hashlib.sha256(summary_path.read_bytes()).hexdigest(),
        observations=12,conditions=6,seeds_per_condition=2,
        csv_means_match_saved_summary=True),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='complete',conditions=6,observations=12,source_means_verified=True,output=str(OUT)),indent=2))


if __name__=='__main__':main()
