"""Build external-decision cases; the public runner supplies the real Jev engine."""
from collections import defaultdict
from orgabm.sdk import run_simulation
from .models import CollectiveMobility,Colocation,DynamicGame,RuleEngine


def build_cases():
    cases=[]
    for seed in (7,11):
        for visible in (True,False):
            condition='history_visible' if visible else 'history_hidden'
            cases.append(dict(id=f'ncs-cmm-{condition}-{seed}',paper_id='ncs_cmm_2021',
                environment=CollectiveMobility(seed=seed,memory_visible=visible),rounds=10,seed=seed,condition=condition))
        for policy in ('continuous','remote_return'):
            cases.append(dict(id=f'ncs-colocation-{policy}-{seed}',paper_id='ncs_colocation_2022',
                environment=Colocation(seed=seed,policy=policy),rounds=12,seed=seed,condition=policy))
        for topology in ('ring','star','switching'):
            cases.append(dict(id=f'ncs-dynamic-{topology}-{seed}',paper_id='ncs_dynamic_2026',
                environment=DynamicGame(seed=seed,condition=topology),rounds=100,seed=seed,condition=topology))
    return cases


def run_baselines():
    output=[]
    for case in build_cases():
        env=case['environment'];result=run_simulation(env,RuleEngine(env),rounds=case['rounds'],seed=case['seed'])
        output.append({k:v for k,v in case.items() if k!='environment'}|dict(result=result))
    return output


def summarize(results):
    rows=[]
    for case in results:
        result=case['result'];metrics=result['metrics'];paper=case['paper_id'];row=dict(id=case['id'],paper_id=paper,
            seed=case['seed'],condition=case['condition'],completed_rounds=result['completed_rounds'],decisions=result['decisions'])
        if paper=='ncs_cmm_2021':
            last=metrics[-3:]
            row.update(revisit_rate=sum(m['revisit_rate'] for m in last)/len(last),concentration=sum(m['concentration'] for m in last)/len(last),
                occupied_sites=sum(m['occupied_sites'] for m in last)/len(last))
        elif paper=='ncs_colocation_2022':
            for phase,name in ((0,'baseline'),(1,'intervention'),(2,'return')):
                phase_rows=[m for m in metrics if m['phase']==phase]
                for metric in ('local_bridges','new_ties','cross_department_ties','contact_edges'):
                    row[f'{name}_{metric}']=sum(m[metric] for m in phase_rows)/len(phase_rows)
        elif paper=='ncs_dynamic_2026':row.update(mean_cooperation=metrics[-1]['mean_cooperation'],network_transitions=metrics[-1]['network_transitions'])
        rows.append(row)
    return rows


def contrasts(rows):
    groups=defaultdict(dict)
    for row in rows:groups[row['paper_id'],row['seed']][row['condition']]=row
    out=[]
    for (paper,seed),conditions in groups.items():
        row=dict(paper_id=paper,seed=seed)
        if paper=='ncs_cmm_2021' and len(conditions)==2:
            effect=conditions['history_visible']['revisit_rate']-conditions['history_hidden']['revisit_rate']
            row.update(metric='last3_revisit_visible_minus_hidden',difference=effect,exploratory_transfer_hypothesis_holds=effect>0,
                hypothesis_origin='Framework history-visibility transfer speculation,not a result or predicted direction from the source paper.',
                meaning='Visibility ablation;free rules already reverse the speculative sign.This small menu cannot validate the published macro conclusion.')
        elif paper=='ncs_colocation_2022' and len(conditions)==2:
            effect=conditions['remote_return']['intervention_local_bridges']-conditions['continuous']['intervention_local_bridges']
            row.update(metric='intervention_bridges_remote_minus_continuous',difference=effect,exploratory_transfer_hypothesis_holds=effect<0,
                meaning='Short network-policy contrast on public candidate ties; no private empirical estimate.')
        elif paper=='ncs_dynamic_2026' and len(conditions)==3:
            fixed=(conditions['ring']['mean_cooperation']+conditions['star']['mean_cooperation'])/2
            effect=conditions['switching']['mean_cooperation']-fixed
            row.update(metric='short_run_cooperation_switching_minus_mean_static',difference=effect,expected_direction=None,direction_is_exploratory=True,
                meaning='Exploratory topology contrast; original theorem does not imply this demo pair must favor cooperation.')
        else:continue
        out.append(row)
    return out


def analyze(results):
    """Compare fresh externally supplied runs to free rules without leaking answers."""
    external=summarize(results);baseline=summarize(run_baselines())
    return dict(scope='Decision-level transfers of three published NCS models; no full-paper empirical/theorem replication claim.',
        external_rows=external,paired_rule_rows=baseline,external_contrasts=contrasts(external),paired_rule_contrasts=contrasts(baseline),
        sampling_note='Rule baseline uses case.seed with local question/actor IDs; public Jev ensemble uses seed20261030 and namespaced IDs. These are independent samples, not paired common random numbers.',
        criteria_frozen_before_real_calls=['Every action changes the modeled world;no controller-only requests',
            'Valid graph neighbors/candidate contacts/destinations and conserved population',
            'Contrast signs are descriptive,reported for both seeds without suppressing reversals',
            'Rule agreement is not human accuracy;two seeds and short histories cannot establish population-level effects'],
        actual_jev_status='Determined only from public runner provider response receipts;this module does not call a provider.')
