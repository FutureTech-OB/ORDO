"""Declarative task/authority specification, independent of decision providers."""
import copy
import math
import re
from .personas import validate_population
from .workforce import validate_structure, build_workforce

CAPABILITIES = ['work', 'request', 'revise', 'abandon', 'approve', 'reject', 'wait']
ROLES = {
    'employee': dict(title='Specialist', responsibilities='Execute assigned tasks; request approval when required.',
                     allowed_actions=['work','request','revise','abandon','wait']),
    'manager': dict(title='Department manager', responsibilities='Review submitted proposals within your processing capacity and budget authority.',
                    allowed_actions=['approve','reject','revise','wait']),
}
DEFAULTS = dict(agents=12, departments=3, rounds=12, seed=42, population=None, memory=None,
    structure={'template':'department_hierarchy'}, delegation_limit=0, authority_level='direct',
    review_capacity=1, worker_capacity=1, budget=100, individual_reward_weight=0.5,
    max_revisions=2, engine='threshold', batch_size=64, concurrency=4,
    objective='Complete valuable interdependent tasks within the budget and deadlines.')


def labels(config):
    return [a * config['departments'] // config['agents'] for a in range(config['agents'])]


def reviewer_for(roster, owner, authority_level):
    node, reviewers = roster[owner]['manager'], []
    while node is not None:
        if 'approve' in roster[node]['role_definition']['allowed_actions']:
            reviewers.append(node)
        node = roster[node]['manager']
    return (reviewers[0] if authority_level == 'direct' else reviewers[-1]) if reviewers else None


def validate_workflow(raw):
    if not isinstance(raw, dict) or set(raw)-set(DEFAULTS)-{'tasks'}:
        raise ValueError('Unknown workflow configuration fields.')
    c = {**copy.deepcopy(DEFAULTS), **copy.deepcopy(raw)}
    for key, lo, hi in [('agents',2,10000),('departments',1,1000),('rounds',1,1000),
                        ('seed',0,2**32-1),('review_capacity',1,8),('worker_capacity',1,8),
                        ('max_revisions',0,10),('batch_size',1,128),('concurrency',1,16)]:
        if type(c[key]) is not int or not lo <= c[key] <= hi:
            raise ValueError(f'Invalid workflow {key}; expected integer {lo}..{hi}.')
    if c['agents'] < c['departments']*2:
        raise ValueError('Provide at least two members per department.')
    for key, hi in [('budget',1e9),('delegation_limit',1e9),('individual_reward_weight',1)]:
        if type(c[key]) not in (float,int) or not math.isfinite(c[key]) or not 0 <= c[key] <= hi:
            raise ValueError(f'Invalid workflow {key}.')
    if c['authority_level'] not in ('direct','top') or c['engine'] not in ('threshold','permissive','jev'):
        raise ValueError('Unknown authority level or workflow engine.')
    if not isinstance(c['objective'],str) or not c['objective'] or len(c['objective']) > 2000:
        raise ValueError('Provide an objective of at most 2,000 characters.')
    c['population'] = validate_population(c['population'], c['agents'])
    if c['structure'] is None:
        raise ValueError('Workflow requires an explicit organization structure.')
    c['structure'] = validate_structure(c['structure'],c['agents'],c['departments'],
        capabilities=CAPABILITIES,default_roles=ROLES,required_action='wait',min_department_size=2)
    roster = build_workforce(c, labels(c))
    from .memory import validate_memory
    c['memory'] = validate_memory(c['memory'],roster)
    tasks = c.get('tasks')
    if not isinstance(tasks,list) or not 1 <= len(tasks) <= 10000:
        raise ValueError('Provide 1..10,000 explicit tasks.')
    normalized, ids = [], set()
    for task in tasks:
        if not isinstance(task,dict) or set(task)-{'id','title','owner','dependencies','effort','revision_effort','cost','value','signal','success_probability','deadline'}:
            raise ValueError('Unknown task fields.')
        t = dict(title=task.get('id',''), dependencies=[], effort=2, revision_effort=1,
                 cost=1, value=5, signal=0.7, success_probability=0.7, deadline=c['rounds'])
        t.update(task)
        if not isinstance(t.get('id'),str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',t['id']) or t['id'] in ids:
            raise ValueError('Task IDs must be unique alphanumeric/underscore/hyphen strings.')
        if not isinstance(t['title'],str) or not t['title'] or len(t['title']) > 1000:
            raise ValueError('Invalid task title.')
        owner = t.get('owner')
        if type(owner) is not int or not 0 <= owner < c['agents'] or 'work' not in roster[owner]['role_definition']['allowed_actions']:
            raise ValueError('Task owner must have the work capability.')
        for key in ['effort','revision_effort','deadline']:
            if type(t[key]) is not int or not 1 <= t[key] <= 100000:
                raise ValueError('Task effort, revision effort and deadline must be positive integers.')
        for key in ['cost','value','signal','success_probability']:
            hi = 1 if key in ['signal','success_probability'] else 1e9
            if type(t[key]) not in (int,float) or not math.isfinite(t[key]) or not 0 <= t[key] <= hi:
                raise ValueError(f'Invalid task {key}.')
        deps = t['dependencies']
        if not isinstance(deps,list) or any(not isinstance(x,str) for x in deps) or len(set(deps)) != len(deps) or t['id'] in deps:
            raise ValueError('Invalid task dependencies.')
        if t['cost'] > c['delegation_limit']:
            if reviewer_for(roster,owner,c['authority_level']) is None or 'request' not in roster[owner]['role_definition']['allowed_actions']:
                raise ValueError('Tasks above delegation limit need a reachable approving manager and request capability.')
        ids.add(t['id']); normalized.append(t)
    children, indegree = {i:[] for i in ids}, {}
    for t in normalized:
        if set(t['dependencies'])-ids:
            raise ValueError('Unknown task dependency.')
        indegree[t['id']] = len(t['dependencies'])
        for parent in t['dependencies']:
            children[parent].append(t['id'])
    ready = [i for i,n in indegree.items() if n == 0]
    count = 0
    while ready:
        parent = ready.pop(); count += 1
        for child in children[parent]:
            indegree[child] -= 1
            if indegree[child] == 0: ready.append(child)
    if count != len(tasks):
        raise ValueError('Task dependencies must be acyclic.')
    c['tasks'] = normalized
    return c


def workload(config):
    roster = build_workforce(config, labels(config))
    workers = len({t['owner'] for t in config['tasks']})
    managers = len({m for t in config['tasks'] if (m := reviewer_for(roster,t['owner'],config['authority_level'])) is not None})
    batch = config['batch_size']
    return dict(decisions=config['rounds']*(workers+managers*config['review_capacity']),
        provider_requests=config['rounds']*(math.ceil(workers/batch)+config['review_capacity']*math.ceil(managers/batch)),
        workers=workers, reviewers=managers)
