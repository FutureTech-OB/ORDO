"""Explicit synthetic cookbook assumptions, separate from ORDO's core."""
import copy
import json
from pathlib import Path
from orgabm.sdk import FunctionEngine
from orgabm.templates import workflow_plan

ROOT = Path(__file__).resolve().parents[2]
SEEDS = [7, 8, 9]
RECIPES = {'01': 'Knowledge sharing and adoption rights', '02': 'Approval bottlenecks and delegation',
           '03': 'Risk-information disclosure', '04': 'Build an organization from a Persona pool', '05': 'Scale the same workflow to 1,000 members'}


def learning_plan():
    return json.loads((ROOT/'examples/templates/plans/contact_permission_comparison.json').read_text(encoding='utf-8'))


def authority_plan():
    plan = workflow_plan('authority_comparison')
    plan['vary'] = {'delegation_limit': [0, 2], 'review_capacity': [1, 2]}
    return plan


def disclosure_plan(policy):
    if policy not in ('manager_only', 'shared_now', 'shared_round_3'):
        raise ValueError('Unknown disclosure policy.')
    plan = workflow_plan('functional_hierarchy')
    base = plan['base']
    base.update(rounds=8, budget=100, review_capacity=1, delegation_limit=0)
    workers = [1, 2, 3, 5, 6, 7, 9, 10, 11]
    tasks, reports = [], {d: {} for d in range(3)}
    for wave in range(3):
        for i, owner in enumerate(workers):
            probability = .15 if (i + wave) % 3 == 0 else .85
            tid = f'project_{wave}_{owner}'
            tasks.append(dict(id=tid, title=f'Synthetic project {wave}-{owner}', owner=owner,
                              dependencies=[], effort=1, cost=3, value=10,
                              signal=.8, success_probability=probability, deadline=wave+3))
            reports[owner//4][tid] = probability
    base['tasks'] = tasks
    trees = []
    for department, estimates in reports.items():
        grants = [dict(audience=[{'roles': ['manager']}], level='detail', from_round=1)]
        if policy != 'manager_only':
            grants.append(dict(audience=[{'roles': ['employee']}], level='detail',
                               from_round=1 if policy == 'shared_now' else 3))
        trees.append(dict(id=f'department_{department}', scope='department', owner=department,
                          nodes=[dict(id='due_diligence', title='Project due-diligence report',
                                      summary='Synthetic assessment records for projects in this department.',
                                      content=json.dumps({'estimates': estimates}, ensure_ascii=False),
                                      grants=grants)]))
    base['memory'] = dict(organization_id='cookbook_org', trees=trees, max_items=20, max_chars=8000)
    plan['vary'], plan['seeds'] = {}, list(SEEDS)
    return plan


def information_rule():
    """Declared risk-neutral rule; reports are stipulated accurate in this toy case.

    Only delivered detailed reports can change the estimate. This demonstrates
    an information mechanism; it is not a learned model of human judgment.
    """
    def choose(state, question):
        observation = json.loads(question['instructions'])
        task, choices = observation['task'], question['criteria']
        estimate = task['signal']
        for item in observation.get('memory', {}).get('items', []):
            if item.get('level') == 'detail' and item.get('node_id') == 'due_diligence':
                estimate = json.loads(item['content'])['estimates'].get(task['id'], estimate)
        acceptable = estimate * task['value'] >= task['cost']
        if observation['stage'] == 'proposal':
            if task['status'] == 'revision' and 'revise' in choices: action = 'revise'
            elif task['status'] in ('approved', 'active') and 'work' in choices: action = 'work'
            elif not acceptable and 'abandon' in choices: action = 'abandon'
            elif 'work' in choices: action = 'work'
            elif 'request' in choices: action = 'request'
            else: action = 'wait'
        else:
            action = 'approve' if acceptable and 'approve' in choices else 'reject' if 'reject' in choices else 'wait'
        return {a: float(a == action) for a in choices}
    return FunctionEngine(choose, name='cookbook-explicit-information-rule')


def synthetic_pool():
    return [dict(id=f'fictional-candidate-{i}', name=f'Fictional candidate {i}',
                 description='Synthetic Persona for demonstrating population construction.',
                 background={'occupation': 'team_lead' if i < 6 else 'specialist'},
                 source={'dataset': 'ORDO cookbook synthetic pool', 'synthetic': True}) for i in range(24)]


def assignment_job(mode, threshold=.5):
    config = workflow_plan('functional_hierarchy')['base']
    config['population'] = dict(records=synthetic_pool(), sampling='without_replacement', seed=2026)
    return dict(scenario='task_workflow', config=config, mode=mode, seed=2026,
                threshold=threshold, batch_size=4, max_evaluations=48,
                context='A fictional organization with department managers and specialists.')


def occupancy_fixture():
    """Invented scores for offline plumbing; never presented as Jev output."""
    def choose(state, question):
        data = json.loads(question['instructions'])
        leader = data['persona']['background']['occupation'] == 'team_lead'
        manager = data['position']['title'] == 'Department manager'
        probability = (.9 if leader else .2) if manager else (.35 if leader else .85)
        return {'holds_position': probability, 'does_not_hold_position': 1-probability}
    return FunctionEngine(choose, name='synthetic-occupancy-score-fixture')


def cases(recipe, scale_agents=1000):
    if recipe == '01': return [('contact_x_permission', learning_plan(), 'registered')]
    if recipe == '02': return [('delegation_x_capacity', authority_plan(), 'registered')]
    if recipe == '03':
        return [(f'{policy}__{engine}', disclosure_plan(policy), engine)
                for engine in ('information_rule', 'memory_blind_control')
                for policy in ('manager_only', 'shared_now', 'shared_round_3')]
    if recipe == '05':
        from examples.large_organization import large_organization_plan
        result = []
        for size in sorted({100, scale_agents}):
            for mode in ('reviewed', 'delegated'):
                plan = large_organization_plan(size, rounds=12, mode=mode)
                # Give reviewed tasks time to finish; do not mechanically censor
                # every reviewed task by making effort equal to the run horizon.
                for task in plan['base']['tasks']:
                    task.update(effort=3, deadline=8)
                result.append((f'n{size}_{mode}', plan, 'registered'))
        return result
    if recipe == '04': return []
    raise ValueError('Unknown recipe.')


def live_plan(plan):
    result = copy.deepcopy(plan)
    result['decision'] = dict(provider='jev', batch_size=64, concurrency=4)
    return result
