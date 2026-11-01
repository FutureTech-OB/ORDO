"""Show positive and unsupported pilot directions together, with no fidelity score."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    output=Path('docs/jev_validation')
    nc=json.loads((output/'nc_analysis.json').read_text(encoding='utf-8'))['papers']
    sa=json.loads((output/'sa_analysis.json').read_text(encoding='utf-8'))['cases']
    fig,axes=plt.subplots(2,2,figsize=(11,7.5),layout='constrained')
    ax=axes[0,0]
    reward=nc['nc_social_rewarding']['late_means_by_information']
    ax.bar(['0','0.5','1'],[reward[k]['cooperation'] for k in ('0','0.5','1')],color='#2b7a78')
    ax.set(title='NC: reputation and cooperation — direction observed',xlabel='Reputation information probability',
           ylabel='Expected cooperation from strategy mix',ylim=(0,1.05))
    ax.text(.02,.9,'2 seeds; final two of 6 synchronous sweeps',transform=ax.transAxes,fontsize=9)
    ax=axes[0,1]
    conditions=['star_r3','star_r6','complete_r6'];labels=['Star, r=3','Star, r=6','Complete, r=6']
    groups=[[r['final_cooperation'] for r in sa if r['paper_id']=='sa_wang_su_2026' and r['condition']==c] for c in conditions]
    ax.bar(labels,[sum(g)/len(g) for g in groups],color='#2b7a78')
    for i,g in enumerate(groups):ax.scatter([i-.05,i+.05],g,color='#253858',s=25,zorder=3)
    ax.set(title='Science Advances: network PGG — direction observed',ylabel='Final fraction cooperating',ylim=(0,1.05))
    ax.text(.02,.9,'2 seeds × 4 colonies; 60 updates; some remain mixed',transform=ax.transAxes,fontsize=9)
    ax=axes[1,0]
    pd=nc['nc_repeated_games']['late_mutual_cooperation_by_incident']
    ax.bar(list(pd),list(pd.values()),color='#bc6545')
    ax.axhline(.5,color='gray',linestyle='--',linewidth=1,label='Exploratory recovery criterion')
    ax.set(title='NC: repeated PD — recovery criterion not met',xlabel='Observed initial incident',
           ylabel='Late mutual-cooperation fraction',ylim=(0,1.05))
    ax.legend(fontsize=8)
    ax=axes[1,1]
    forage=nc['nc_collective_foraging']['mean_group_rewards']
    benefit=[forage[f'{p}_cues1']-forage[f'{p}_cues0'] for p in ('smooth','random')]
    ax.bar(['Clustered','Random'],benefit,color='#bc6545')
    ax.axhline(0,color='gray',linewidth=1)
    ax.set(title='NC: collective foraging — cue interaction not observed',ylabel='Cue-on minus cue-off group rewards')
    ax.text(.02,.05,'2 seeds; one map per type; 120 physical steps',transform=ax.transAxes,fontsize=9)
    fig.suptitle('Fresh Jev pilot choices in paper-derived ABMs\nExecution succeeds; behavioral agreement varies',fontsize=15)
    fig.savefig(output/'pilot_directions.png',dpi=170)
    fig.savefig(output/'pilot_directions.pdf')
    plt.close(fig)


if __name__=='__main__':main()
