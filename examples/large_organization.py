"""Generate a synthetic, multilevel single-organization scaling workload.

No API calls. This is a throughput fixture, not a calibrated organization model.
"""
import argparse
import copy
import json
from pathlib import Path
from orgabm.workflow import ROLES


def large_organization_plan(agents=1000, *, rounds=6, mode='delegated', seed=7):
    if type(agents) is not int or not 20 <= agents <= 10000 or agents % 10:
        raise ValueError('Use 20..10,000 members in complete departments of ten.')
    if type(rounds) is not int or not 1 <= rounds <= 1000:
        raise ValueError('Use 1..1,000 rounds.')
    if mode not in ('delegated','reviewed'):
        raise ValueError('Mode must be delegated or reviewed.')
    assignments,personas,tasks=[],[],[]
    for agent in range(agents):
        department=agent//10
        head=agent%10==0
        manager=(10*((department-1)//10) if head else 10*department) if agent else None
        assignments.append(dict(agent=agent,department=department,
            role='manager' if head else 'employee',manager=manager))
        personas.append(dict(id=f'synthetic-{agent}',
            description=f'Fictional benchmark member {agent}; experienced in routine organizational tasks.',
            source={'kind':'synthetic_scaling_fixture'}))
        if not head:
            tasks.append(dict(id=f'work-{agent}',owner=agent,title='Synthetic task for throughput measurement',
                effort=rounds,cost=2,value=8,signal=.8,success_probability=1,deadline=rounds))
    return dict(scenario='task_workflow',base=dict(agents=agents,departments=agents//10,rounds=rounds,
        structure=dict(template='custom',roles=copy.deepcopy(ROLES),assignments=assignments),
        population=dict(records=personas,sampling='ordered',seed=2026),tasks=tasks,
        delegation_limit=2 if mode=='delegated' else 0,review_capacity=1,
        budget=2*len(tasks),individual_reward_weight=.5,
        objective='Synthetic workload for measuring a multilevel organization runtime; not a behavioral study.'),
        vary={},seeds=[seed],decision=dict(provider='rule',rule='threshold'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agents',type=int,default=1000)
    parser.add_argument('--rounds',type=int,default=6)
    parser.add_argument('--mode',choices=['delegated','reviewed'],default='delegated')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    plan=large_organization_plan(args.agents,rounds=args.rounds,mode=args.mode)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(plan,stream,ensure_ascii=False,indent=2)
    print(str(args.output))


if __name__=='__main__':main()
