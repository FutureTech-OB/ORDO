"""Public integration entrypoint for the shared live-Jev runner."""
from collections import Counter
import statistics
from examples.llm_abm_cookbook.environments import NamingGame,MajorityOpinion,digest
from .pgg import PublicGoodsPC


class FreshNaming(NamingGame):
    def __init__(self,*,committed=0,seed=7):
        super().__init__(agents=24,options=('Q','M'),memory_size=5,seed=seed)
        self.committed=committed
        if committed:
            self.committed_to='M'
            for a,row in self.agents.items():
                row.update(my_history=['Q']*5,partner_history=['Q']*5,
                           outcome=[100]*5,score_history=[100,200,300,400,500],score=500)
                row['committed_tag']=a>self.n-committed
        self.initial_sha256=digest(self.agents)

    def describe(self):
        return dict(super().describe(),committed_members=self.committed,
                    committed_to=self.committed_to,
                    initial_convention='five Q/Q successes per individual' if self.committed else 'no history',
                    reproduction_scope='Fresh external model substitution; two-option selected protocol; no full tipping-threshold estimate.')

    def advance(self,t,actions,probabilities):
        metrics=super().advance(t,actions,probabilities)
        latest=[self.committed_to if row['committed_tag'] else row['my_history'][-1]
                for row in self.agents.values() if row['committed_tag'] or row['my_history']]
        counts=Counter(latest)
        metrics.update(observed_members=len(latest),latest_choice_counts=dict(counts),
                       latest_M_fraction=counts['M']/len(latest) if latest else 0,
                       latest_dominance=max(counts.values())/len(latest) if latest else 0,
                       full_private_state_sha256=digest(self.agents),
                       private_local_memory={str(a):self.local_view(a) for a in self.agents})
        return metrics


def build_cases():
    cases=[]
    for seed in (7,19):
        for committed in (0,4,5):
            condition=f'committed_{committed}'
            cases.append(dict(id=f'sa-naming-{condition}-s{seed}',paper_id='sa_ashery_2025',
                              environment=FreshNaming(committed=committed,seed=seed),rounds=96,seed=seed,condition=condition))
        for n in (20,50):
            cases.append(dict(id=f'sa-majority-n{n}-s{seed}',paper_id='sa_demarzo_2026',
                              environment=MajorityOpinion(agents=n,seed=seed),rounds=4*n,seed=seed,condition=f'N_{n}'))
        for topology,synergy in [('star',3.),('star',6.),('complete',6.)]:
            condition=f'{topology}_r{synergy:g}'
            cases.append(dict(id=f'sa-pgg-{condition}-s{seed}',paper_id='sa_wang_su_2026',
                              environment=PublicGoodsPC(agents=10,colonies=4,topology=topology,synergy=synergy,seed=seed),
                              rounds=60,seed=seed,condition=condition))
    return cases


def analyze(results):
    """Report observed outcomes and prespecified qualitative checks separately."""
    rows=[]
    for entry in results:
        meta=entry.get('case',entry);result=entry['result'];metrics=result.get('metrics',[])
        if not metrics:continue
        last=metrics[-1];paper=meta['paper_id'];row=dict(id=meta['id'],paper_id=paper,condition=meta['condition'],seed=meta['seed'],
            completed_rounds=result.get('completed_rounds'),decisions=result.get('decisions'),run_status=result.get('status'))
        if paper=='sa_ashery_2025':
            row.update(final_recent_success=last['recent_success'],final_latest_M_fraction=last['latest_M_fraction'],
                       final_latest_dominance=last['latest_dominance'],
                       observed_high_coordination=last['recent_success']>=.9)
        elif paper=='sa_demarzo_2026':
            row.update(final_coordination=last['coordination'],reached_consensus=any(m['consensus'] for m in metrics),
                       first_consensus_update=next((m['update'] for m in metrics if m['consensus']),None))
        elif paper=='sa_wang_su_2026':
            row.update(final_cooperation=last['cooperation_fraction'],final_colony_cooperation=last['colony_cooperation'],
                       fully_cooperative=last['fully_cooperative'],fully_defective=last['fully_defective'],
                       active_colonies=last['active_colonies'],neutral_single_mutant_baseline=.1)
        rows.append(row)
    return dict(cases=rows,expected_directions={
        'sa_ashery_2025':'Repeated personal interaction can yield coordination; more committed M members may overturn an established Q convention. Short, two-seed pilots cannot locate a tipping threshold.',
        'sa_demarzo_2026':'Inspect endogenous coordination and consensus as N changes; the original paper reports model-dependent majority attraction and size limits. Do not presume Jev shares a published model\'s beta.',
        'sa_wang_su_2026':'The original weak-selection PC mechanism favors cooperation on stars beyond a topology-dependent synergy threshold; complete graphs remain unfavorable. With Jev probabilities substituted, these are hypotheses to test, not guaranteed predictions.'},
        evidence_boundary='Fresh live inference must be established by the shared runner logs. Completed execution is not reproduction of a paper conclusion. No target outcomes or original behavioral-rule answers are provided to Jev.')
