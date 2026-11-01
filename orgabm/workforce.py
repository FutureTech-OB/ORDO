"""Roles/reporting structure separate from stable Personas and mutable ABM state."""
import copy
from .personas import build_population, digest

CAPABILITIES = ['keep', 'explore', 'copy']
DEFAULT_ROLES = {
    'employee': {'title': 'Employee', 'responsibilities': 'Improve your work process.', 'allowed_actions': CAPABILITIES},
    'manager': {'title': 'Department manager', 'responsibilities': 'Coordinate the department while improving your own work process.',
                'allowed_actions': CAPABILITIES},
}


def validate_structure(raw, agents, departments, *, capabilities=None, default_roles=None,
                       required_action='keep', min_department_size=4):
    capabilities = CAPABILITIES if capabilities is None else capabilities
    default_roles = DEFAULT_ROLES if default_roles is None else default_roles
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw)-{'template', 'roles', 'assignments'}:
        raise ValueError('structure accepts template, roles and assignments.')
    template = raw.get('template', 'flat')
    if template not in ['flat', 'department_hierarchy', 'custom']:
        raise ValueError('Unknown structure template.')
    roles = raw.get('roles', default_roles)
    if not isinstance(roles, dict) or not roles or len(roles) > 100:
        raise ValueError('Provide between 1 and 100 role definitions.')
    normalized = {}
    for role_id, role in roles.items():
        if not isinstance(role_id, str) or not role_id or len(role_id) > 100 or not isinstance(role, dict) or set(role)-{'title', 'responsibilities', 'allowed_actions'}:
            raise ValueError('Invalid role definition.')
        title, duties = role.get('title', role_id), role.get('responsibilities', '')
        if not isinstance(title, str) or not title or len(title) > 200 or not isinstance(duties, str) or len(duties) > 4000:
            raise ValueError('Role title/responsibilities must be bounded text.')
        actions = role.get('allowed_actions', capabilities)
        if not isinstance(actions, list) or any(x not in capabilities for x in actions) or required_action not in actions or len(set(actions)) != len(actions):
            raise ValueError(f'Role actions must be unique entries from {capabilities} and include {required_action}.')
        normalized[role_id] = dict(title=title, responsibilities=duties, allowed_actions=list(actions))
    required = ['employee', 'manager'] if template == 'department_hierarchy' else ['employee'] if template == 'flat' else []
    if any(key not in normalized for key in required):
        raise ValueError('Template role definitions are missing.')
    result = dict(template=template, roles=normalized)
    if template != 'custom':
        if 'assignments' in raw:
            raise ValueError('Explicit assignments require the custom template.')
        return result
    rows = raw.get('assignments')
    if not isinstance(rows, list) or len(rows) != agents:
        raise ValueError('Custom structure requires one assignment per agent.')
    by_agent = {}
    for row in rows:
        if not isinstance(row, dict) or set(row)-{'agent', 'department', 'role', 'manager'}:
            raise ValueError('Unknown assignment fields.')
        agent, department, manager = row.get('agent'), row.get('department'), row.get('manager')
        if type(agent) is not int or not 0 <= agent < agents or agent in by_agent:
            raise ValueError('Assignment agent IDs must be unique indices.')
        if type(department) is not int or not 0 <= department < departments:
            raise ValueError('Assignment department must be a valid zero-based index.')
        if not isinstance(row.get('role'), str) or row['role'] not in normalized:
            raise ValueError('Assignment references an undefined role.')
        if manager is not None and (type(manager) is not int or not 0 <= manager < agents or manager == agent):
            raise ValueError('Invalid manager reference.')
        by_agent[agent] = dict(agent=agent, department=department, role=row['role'], manager=manager)
    counts = [0] * departments
    for row in by_agent.values():
        counts[row['department']] += 1
    if min(counts) < min_department_size:
        raise ValueError(f'Each custom department needs at least {min_department_size} members.')
    # Linear-time forest validation, including deep hierarchies (no recursion).
    done = set()
    for agent in by_agent:
        visiting, node = set(), agent
        while node is not None and node not in done:
            if node in visiting:
                raise ValueError('Reporting relationships must be acyclic.')
            visiting.add(node)
            node = by_agent[node]['manager']
        done.update(visiting)
    result['assignments'] = [by_agent[a] for a in range(agents)]
    return result


def build_workforce(config, labels):
    personas = build_population(config)
    structure = config.get('structure')
    roles = structure['roles'] if structure else DEFAULT_ROLES
    rows = [dict(agent=a, department=d, role='employee', manager=None) for a, d in enumerate(labels)]
    if structure and structure['template'] == 'custom':
        rows = copy.deepcopy(structure['assignments'])
    elif structure and structure['template'] == 'department_hierarchy':
        heads = {}
        for row in rows:
            heads.setdefault(row['department'], row['agent'])
        for row in rows:
            head = heads[row['department']]
            row.update(role='manager' if head == row['agent'] else 'employee',
                       manager=None if head == row['agent'] else head)
    reports = {a: [] for a in range(len(rows))}
    for row in rows:
        if row['manager'] is not None:
            reports[row['manager']].append(row['agent'])
    for row, persona in zip(rows, personas):
        row.update(persona=persona, role_definition=copy.deepcopy(roles[row['role']]),
                   direct_reports=reports[row['agent']])
    return rows


def workforce_metadata(config, rows):
    return dict(population_sha256=digest([r['persona'] for r in rows]),
                organization_sha256=digest([{k:v for k,v in r.items() if k != 'persona'} for r in rows]),
                persona_enabled=config.get('population') is not None,
                structure_enabled=config.get('structure') is not None,
                population_size=len(rows),
                distinct_personas=len({r['persona']['id'] for r in rows if r['persona']}),
                workforce=rows)


def allowed_actions(row):
    capabilities = row['role_definition']['allowed_actions']
    return ['keep'] + (['explore'] if 'explore' in capabilities else []) + (
        [f'copy_{i}' for i in range(3)] if 'copy' in capabilities else [])
