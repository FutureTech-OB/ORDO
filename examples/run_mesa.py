"""Run from repository root: python -m examples.run_mesa"""
from orgabm.mesa_bridge import organization_adapter, organization_rule
from orgabm.sdk import run_simulation

config = dict(agents=120, rounds=20, departments=4, contact='bridge', seed=42)
result = run_simulation(organization_adapter(config), organization_rule('best'),
                        rounds=config['rounds'], seed=config['seed'])
print({'status':result['status'],'decisions':result['decisions'],'final':result['metrics'][-1]})
