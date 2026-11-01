"""JSON experiment plans for the registered organization scenario.

Custom environments use sdk.run_simulation directly; no remote arbitrary-code loader.
"""
from itertools import product
import math
from .organization import validate_config


def expand_plan(plan):
    allowed = {'scenario','base','vary','seeds','decision'}
    if not isinstance(plan,dict) or set(plan)-allowed:
        raise ValueError('Unknown experiment plan fields.')
    scenario = plan.get('scenario','nk_organization')
    if scenario not in ('nk_organization','task_workflow'):
        raise ValueError('Registered scenarios: nk_organization, task_workflow. Custom ABMs use the Python SDK.')
    if scenario == 'task_workflow':
        from .workflow import validate_workflow, workload
        validator, default_rule = validate_workflow, 'threshold'
    else:
        validator, default_rule = validate_config, 'best'
    base, vary, seeds = plan.get('base',{}), plan.get('vary',{}), plan.get('seeds',[42])
    if not isinstance(base,dict) or not isinstance(vary,dict) or not isinstance(seeds,list) or not seeds:
        raise ValueError('base/vary must be objects and seeds a nonempty list.')
    if {'seed','engine','batch_size','concurrency'} & (set(base)|set(vary)):
        raise ValueError('Specify seeds and decision engine in their dedicated fields.')
    if any(type(s) is not int or not 0 <= s < 2**32 for s in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError('Seeds must be distinct nonnegative 32-bit integers.')
    if any(not isinstance(v,list) or not v for v in vary.values()):
        raise ValueError('Every varied parameter needs a nonempty value list.')
    if math.prod(map(len,vary.values()))*len(seeds)>200:
        raise ValueError('Prototype limit: 200 worlds per plan.')
    decision = plan.get('decision',{'provider':'rule','rule':default_rule})
    if not isinstance(decision,dict) or set(decision)-{'provider','rule','batch_size','concurrency'}:
        raise ValueError('Invalid decision specification. Credentials are not configuration fields.')
    provider = decision.get('provider','rule')
    if provider not in ['rule','jev']:
        raise ValueError('Plan service supports rule/jev. Chat models belong to the research assistant; optional comparators use the Python SDK.')
    rule = decision.get('rule',default_rule)
    if rule not in (['threshold','permissive'] if scenario=='task_workflow' else ['best','conformity']):
        raise ValueError('Unknown rule.')
    for key,default,high in [('concurrency',4,16),('batch_size',64,128)]:
        if type(decision.get(key,default)) is not int or not 1 <= decision.get(key,default) <= high:
            raise ValueError('Invalid decision request limits.')
    configs=[]
    for values in product(*vary.values()):
        for seed in seeds:
            configs.append(validator({**base,**dict(zip(vary,values)),'seed':seed,
                'engine':'jev' if provider=='jev' else rule,
                'batch_size':decision.get('batch_size',64),'concurrency':decision.get('concurrency',4)}))
    count=sum(workload(c)['decisions'] if scenario=='task_workflow' else c['agents']*c['rounds'] for c in configs)
    if count>2_000_000:
        raise ValueError('Prototype limit: two million decisions per plan.')
    return dict(scenario=scenario,decision={**decision,'rule':rule},configs=configs,worlds=len(configs),
                decisions=count,counts_are_upper_bounds=scenario=='task_workflow',
                provider_requests=sum(workload(c)['provider_requests'] if scenario=='task_workflow' else math.ceil(c['agents']/decision.get('batch_size',64))*c['rounds'] for c in configs) if provider=='jev' else 0,
                batching='Fresh questions, synchronized within each stage; later stages use earlier decisions.' if scenario=='task_workflow' else 'fresh per-agent questions in native Jev batches, synchronized each round' if provider=='jev' else 'local rules')
