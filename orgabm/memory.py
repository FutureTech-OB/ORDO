"""Permission-filtered organizational memory forests.

Ownership describes where information belongs; readers and node grants describe
access. Only the returned view belongs in an agent's decision input. The audit
and complete policy are researcher data, never a shared provider state.
"""
import copy
import json
import re
from collections import defaultdict, deque
from .personas import digest

LEVELS = {'summary':1, 'detail':2}


def _id(value):
    return isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}',value)


def _audience(value, agents, departments, roles):
    if not isinstance(value,list) or len(value)>1000:
        raise ValueError('Memory audiences must be lists of at most 1,000 selectors.')
    out=[]
    for selector in value:
        if not isinstance(selector,dict) or not selector or set(selector)-{'everyone','agents','departments','roles'}:
            raise ValueError('Invalid memory audience selector.')
        if 'everyone' in selector:
            if selector != {'everyone':True} or type(selector['everyone']) is not bool:
                raise ValueError('everyone: true must be an explicit standalone selector.')
        else:
            for key,valid in [('agents',agents),('departments',departments),('roles',roles)]:
                if key not in selector:continue
                values=selector[key]
                expected_type=str if key=='roles' else int
                if (not isinstance(values,list) or not values or
                    any(type(x) is not expected_type or x not in valid for x in values) or len(set(values))!=len(values)):
                    raise ValueError(f'Memory selector references invalid {key}.')
        out.append(copy.deepcopy(selector))
    return out


def validate_memory(raw, roster, roles=None):
    if raw is None:return None
    if not isinstance(raw,dict) or set(raw)-{'organization_id','trees','max_items','max_chars'}:
        raise ValueError('Unknown organizational memory fields.')
    organization=raw.get('organization_id','org-0')
    if not _id(organization):raise ValueError('Invalid memory organization_id.')
    result=dict(organization_id=organization,max_items=raw.get('max_items',20),max_chars=raw.get('max_chars',8000),trees=[])
    for key,lo,hi in [('max_items',1,200),('max_chars',128,64000)]:
        if type(result[key]) is not int or not lo<=result[key]<=hi:
            raise ValueError(f'Invalid memory {key}.')
    trees=raw.get('trees')
    if not isinstance(trees,list) or len(trees)>10000:
        raise ValueError('memory.trees must be a list of at most 10,000 trees.')
    agents={r['agent'] for r in roster};departments={r['department'] for r in roster}
    roles=set(roles) if roles is not None else {r['role'] for r in roster}
    seen,total=set(),0
    for raw_tree in trees:
        if not isinstance(raw_tree,dict) or set(raw_tree)-{'id','scope','owner','readers','nodes'}:
            raise ValueError('Unknown memory tree fields.')
        tree=copy.deepcopy(raw_tree)
        if not _id(tree.get('id')) or tree['id'] in seen:
            raise ValueError('Memory tree IDs must be unique safe strings.')
        seen.add(tree['id'])
        scope,owner=tree.get('scope'),tree.get('owner')
        if scope=='organization':
            if owner is not None:raise ValueError('Organization trees do not take an owner index.')
            default=[{'everyone':True}]
        elif scope in ('department','personal'):
            if type(owner) is not int or owner not in (departments if scope=='department' else agents):
                raise ValueError('Invalid memory tree owner.')
            default=[{'departments' if scope=='department' else 'agents':[owner]}]
        else:raise ValueError('Memory scope must be organization, department or personal.')
        tree['owner']=owner
        tree['readers']=_audience(tree.get('readers',default),agents,departments,roles)
        nodes=tree.get('nodes')
        if not isinstance(nodes,list) or len(nodes)>20000:
            raise ValueError('Memory tree nodes must be a bounded list.')
        total+=len(nodes)
        if total>20000:raise ValueError('At most 20,000 configured memory nodes per world.')
        normalized,by_id=[],{}
        for raw_node in nodes:
            if not isinstance(raw_node,dict) or set(raw_node)-{'id','parent','title','summary','content','grants'}:
                raise ValueError('Unknown memory node fields.')
            node=dict(parent=None,summary='',content='',grants=None,**{k:v for k,v in raw_node.items() if k not in ('parent','summary','content','grants')})
            node.update(copy.deepcopy(raw_node))
            if not _id(node.get('id')) or node['id'] in by_id:
                raise ValueError('Memory node IDs must be unique within a tree.')
            for key,limit in [('title',200),('summary',2000),('content',16000)]:
                if not isinstance(node.get(key),str) or len(node[key])>limit or (key=='title' and not node[key]):
                    raise ValueError(f'Invalid memory node {key}.')
            if node['parent'] is not None and not _id(node['parent']):
                raise ValueError('Invalid memory parent ID.')
            grants=node['grants']
            if grants is not None:
                if not isinstance(grants,list) or len(grants)>100:
                    raise ValueError('Node grants must be null (inherit) or a bounded list.')
                normalized_grants=[]
                for grant in grants:
                    if not isinstance(grant,dict) or set(grant)-{'audience','level','from_round','until_round'}:
                        raise ValueError('Invalid memory grant.')
                    start,end=grant.get('from_round',1),grant.get('until_round')
                    if type(start) is not int or not 1<=start<=100000:
                        raise ValueError('Invalid memory release round.')
                    if end is not None and (type(end) is not int or not start<=end<=100000):
                        raise ValueError('Invalid memory grant end round.')
                    if not isinstance(grant.get('level'),str) or grant['level'] not in LEVELS:
                        raise ValueError('Grant level must be summary or detail.')
                    normalized_grants.append(dict(audience=_audience(grant.get('audience'),agents,departments,roles),
                        level=grant['level'],from_round=start,until_round=end))
                node['grants']=normalized_grants
            normalized.append(node);by_id[node['id']]=node
        children=defaultdict(list)
        for node in normalized:
            if node['parent'] is not None and node['parent'] not in by_id:
                raise ValueError('Memory parent must exist in the same tree.')
            children[node['parent']].append(node['id'])
        queue=deque((n,1) for n in children[None]);visited=0
        while queue:
            node,depth=queue.popleft();visited+=1
            if depth>64:raise ValueError('Memory trees support at most 64 levels.')
            queue.extend((n,depth+1) for n in children[node])
        if visited!=len(nodes):raise ValueError('Memory parents must form acyclic trees.')
        tree['nodes']=normalized;result['trees'].append(tree)
    return result


def _matches(selector, row):
    if selector.get('everyone'):return True
    return all(row[{'agents':'agent','departments':'department','roles':'role'}[key]] in values
               for key,values in selector.items())


def _allowed(audience, row):
    return any(_matches(selector,row) for selector in audience)


class MemoryForest:
    """Immutable configured memories, read through a trusted roster identity.

    For a node to be visible, the tree gate and every ancestor must permit it.
    Child grants can narrow but cannot broaden an ancestor's disclosure level.
    """
    def __init__(self, policy, roster):
        self.policy=validate_memory(policy,roster)
        if self.policy is None:raise ValueError('MemoryForest requires an explicit policy.')
        self._roster={r['agent']:{k:r[k] for k in ('agent','department','role')} for r in roster}
        self.policy_hash=digest(self.policy)
        self._trees=[];self._everyone=set()
        self._indexes={key:defaultdict(set) for key in ('agents','departments','roles')}
        for i,tree in enumerate(self.policy['trees']):
            children=defaultdict(list)
            for node in tree['nodes']:children[node['parent']].append(node)
            self._trees.append((tree,children))
            for selector in tree['readers']:
                if selector.get('everyone'):self._everyone.add(i)
                else:
                    for key,values in selector.items():
                        for value in values:self._indexes[key][value].add(i)

    def observe(self, agent, round_no, *, organization_id=None):
        if type(agent) is not int or agent not in self._roster or type(round_no) is not int or round_no<1:
            raise ValueError('Use a valid roster member and positive round.')
        row=self._roster[agent]
        candidates=set(self._everyone)
        for key,field in [('agents','agent'),('departments','department'),('roles','role')]:
            candidates.update(self._indexes[key].get(row[field],()))
        if organization_id is not None and organization_id!=self.policy['organization_id']:
            candidates.clear()
        items=[];eligible=0;chars=len(json.dumps({'items':[]},ensure_ascii=False))
        for i in sorted(candidates):
            tree,children=self._trees[i]
            if not _allowed(tree['readers'],row):continue
            stack=[(node,2) for node in reversed(children[None])]
            delivered=set()
            while stack:
                node,parent_level=stack.pop()
                if node['grants'] is None:
                    level=parent_level if node['parent'] is not None else 0
                else:
                    level=max((LEVELS[g['level']] for g in node['grants']
                        if g['from_round']<=round_no and (g['until_round'] is None or round_no<=g['until_round'])
                        and _allowed(g['audience'],row)),default=0)
                    level=min(level,parent_level)
                if not level:continue
                eligible+=1
                item=dict(tree_id=tree['id'],scope=tree['scope'],node_id=node['id'],parent=node['parent'],
                    title=node['title'],level='detail' if level==2 else 'summary',summary=node['summary'])
                if level==2:item['content']=node['content']
                size=len(json.dumps(item,ensure_ascii=False))+(2 if items else 0)
                if (len(items)<self.policy['max_items'] and chars+size<=self.policy['max_chars']
                    and (node['parent'] is None or node['parent'] in delivered)):
                    items.append(item);chars+=size;delivered.add(node['id'])
                stack.extend((child,level) for child in reversed(children[node['id']]))
        view={'items':items}
        audit=dict(policy_sha256=self.policy_hash,eligible_count=eligible,delivered_count=len(items),
            budget_omitted=eligible-len(items),view_chars=chars,view_sha256=digest(view),
            delivered=[{k:item[k] for k in ('tree_id','node_id','level')} for item in items])
        return view,audit
