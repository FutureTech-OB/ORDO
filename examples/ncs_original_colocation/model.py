"""Full candidate, two-stage edge-propensity adapter around the author kernel."""
import ast
from copy import deepcopy
import json
import networkx as nx
import numpy as np
from orgabm.sdk import DecisionBatch,FunctionEngine
from .source import load,author_class,digest,graph_record,memory_record


class StageHooks(ast.NodeTransformer):
    """Only record pre-choice features and yield the two original sampling calls."""
    def __init__(self):self.draw_hooks=0;self.feature_hooks=0;self.day_hooks=0
    def visit_FunctionDef(self,node):
        if node.name!='transform':return node
        return self.generic_visit(node)
    def visit_Assign(self,node):
        target=node.targets[0]
        if isinstance(target,ast.Name) and target.id in ('first_round_probs','second_round_probs'):
            return [node,*ast.parse('self._edge_views = []').body]
        if isinstance(target,ast.Name) and target.id in ('first_round_random_edge_inds','second_round_random_edge_inds'):
            stage=1 if target.id.startswith('first') else 2
            edges='self.all_edges' if stage==1 else 'remaining_edges'
            probs='first_arr_probs' if stage==1 else 'arr_probs'
            count='50+int(size_shifts[day_ind])' if stage==1 else '20+int(size_shifts[day_ind])'
            expression=f"{{'kind':'scores','stage':{stage},'day':day,'edges':{edges},'views':self._edge_views,'native_probabilities':{probs},'size':{count}}}"
            node.value=ast.Yield(ast.parse(expression,mode='eval').body);self.draw_hooks+=1
        return node
    def visit_Expr(self,node):
        value=node.value
        if (isinstance(value,ast.Call) and isinstance(value.func,ast.Attribute)
            and value.func.attr=='append' and isinstance(value.func.value,ast.Name)
            and value.func.value.id in ('first_round_probs','second_round_probs')):
            second=value.func.value.id=='second_round_probs'
            capture=("self._edge_views.append({'distance_m':float(cur_dist),'same_research_unit':bool(same_dpt),"
                     "'contact_five_workdays_ago':bool(present_last_week),'past_contact_decay_sum':float(prev_frequency),"
                     f"'would_close_triangle':{ 'bool(would_close)' if second else 'None'}}})")
            self.feature_hooks+=1
            return [*ast.parse(capture).body,node]
        return node
    def visit_For(self,node):
        node=self.generic_visit(node)
        if (isinstance(node.target,ast.Tuple) and [getattr(x,'id',None) for x in node.target.elts]==['day_ind','day']):
            node.body.extend(ast.parse("yield {'kind':'day','day':day,'graph':G}").body);self.day_hooks+=1
        return node


def staged_class(data):
    root,notebook,dist,dates,memory,params,meta=data
    original,_=author_class(root,dist,dates,daily=False)
    tree=ast.parse(''.join(notebook['cells'][8]['source']));patch=StageHooks();tree=patch.visit(tree)
    if (patch.draw_hooks,patch.feature_hooks,patch.day_hooks)!=(2,2,1):raise ValueError('Pinned author sampling structure changed.')
    ast.fix_missing_locations(tree);space=dict(original.transform.__globals__)
    exec(compile(tree,'<two-stage-author-hook>','exec'),space)
    return space['graph_generator'],digest(ast.dump(tree))


class FullPublicColocation:
    """Score all native candidate edges; the environment samples a fixed quota.

    Choice(contact/not_contact) measures a relative propensity. It is NOT an
    independently executed Bernoulli action or a global no-contact option.
    The environment normalizes the contact scores and performs the unchanged
    global sample without replacement. No native weight enters Jev's prompt.
    """
    def __init__(self,cache='.buildtmp/ncs-colocation-source',numpy_seed=20261030):
        self.data=load(cache);self.root,self.notebook,self.dist,self.dates,self.memory,self.params,self.meta=self.data
        self.cls,self.ast_sha=staged_class(self.data);self.seed=numpy_seed
        self.rng=np.random.RandomState(numpy_seed).get_state();self.phase=-1;self.obj=None;self.iterator=None
        self.payload=None;self.pending=None;self.prefix=None;self.round=0;self.days=[];self.phases=[];self.graphs=[]
        self.score_count=0;self.selected_count=0

    def describe(self):
        return dict(scenario='full_public_capsule_colocation_edge_score_substitution',numpy_seed=self.seed,
            **self.meta,staged_author_ast_sha256=self.ast_sha,total_sdk_stages=1764,
            probability_semantics='contact score normalized over all current candidates; globally quota-sampled without replacement',
            source_weights_exposed_to_model=False,independent_bernoulli_actions_executed=False,
            change='Jev replaces edge weight; source scheduling, quotas, pools, closure and memory remain. Not an exact original decision model.')

    def _resume(self,indices=None,send=False):
        saved=np.random.get_state();np.random.set_state(self.rng)
        try:
            value=self.iterator.send(indices) if send else next(self.iterator)
        finally:
            self.rng=np.random.get_state();np.random.set_state(saved)
        return value

    def _next_phase(self):
        if self.obj is not None:
            self.memory=self.obj.mem_dict
            p=self.meta['phases'][self.phase]
            self.phases.append(dict(phase=p['id'],memory_sha256=digest(memory_record(self.memory))))
            if self.phase==0:self.prefix=deepcopy(self.memory)
        self.phase+=1
        if self.phase==len(self.meta['phases']):return False
        p=self.meta['phases'][self.phase]
        if self.phase==3:self.memory=deepcopy(self.prefix)
        distances={e:(2000,v[1]) for e,v in self.dist.items()} if p['remote'] else self.dist
        self.obj=self.cls(self.memory,distances,**self.params)
        self.iterator=self.obj.transform(None,start=p['start'],end=p['end'])
        return True

    def prepare(self,t):
        if self.pending is not None or t!=self.round+1:raise ValueError('Commit each full stage first.')
        while self.payload is None or self.payload['kind']=='day':
            if self.iterator is None:
                if not self._next_phase():raise StopIteration('Complete public capsule.')
            try:self.payload=self._resume()
            except StopIteration:
                self.iterator=None;self.payload=None
        p=self.payload
        if p['size']<0 or p['size']>len(p['edges']):raise ValueError('Source Gaussian quota is invalid; do not clamp or alter it.')
        questions={};ids={}
        for i,(edge,view) in enumerate(zip(p['edges'],p['views'])):
            qid=f"p{self.phase}_d{p['day']}_s{p['stage']}_e{edge[0]}_{edge[1]}"
            text=('Estimate the chance that this pair of researchers communicate on this workday from these link observations. '
                  'A past-contact decay sum counts earlier contacts with exponential time discount. '
                  'Triangle closure refers only to contacts already formed earlier today. '
                  +json.dumps(view,separators=(',',':')))
            questions[qid]=dict(type='choice',instructions=text,criteria={'contact':'The pair communicate today.','not_contact':'The pair do not communicate today.'})
            ids[qid]=f'edge:{edge[0]}:{edge[1]}'
        if len(questions)!=len(p['edges']):raise AssertionError('All candidates must be scored exactly once.')
        self.pending=(p,questions)
        return DecisionBatch('Estimate each separate pair using only its own link observations.',questions,ids)

    def advance(self,t,actions,probabilities):
        if self.pending is None or t!=self.round+1:raise ValueError('Prepare first.')
        p,questions=self.pending
        if set(probabilities)!=set(questions):raise ValueError('Full candidate coverage is required; no subsampling.')
        weights=np.array([probabilities[q]['contact'] for q in questions],dtype=float)
        if not np.isfinite(weights).all() or (weights<0).any() or (weights>1).any() or weights.sum()<=0 or np.count_nonzero(weights)<p['size']:
            raise ValueError('Cannot quota-sample these edge scores; no epsilon floor or quota changes are allowed.')
        weights/=weights.sum()
        saved=np.random.get_state();np.random.set_state(self.rng)
        try:chosen=np.random.choice(range(len(p['edges'])),replace=False,size=p['size'],p=weights)
        finally:self.rng=np.random.get_state();np.random.set_state(saved)
        selected=[list(p['edges'][i]) for i in chosen]
        self.payload=self._resume(chosen,send=True)
        self.round=t;self.pending=None;self.score_count+=len(weights);self.selected_count+=len(chosen)
        row=dict(stage_number=t,phase=self.meta['phases'][self.phase]['id'],author_day=p['day'],
                 stage=p['stage'],candidates=len(weights),quota=p['size'],selected_edges=selected,
                 selected_sha256=digest(selected),scores_sha256=digest(weights.tolist()),
                 memory_sha256=digest(memory_record(self.obj.mem_dict)))
        if p['stage']==2:
            if self.payload['kind']!='day':raise AssertionError('A source day must complete after its second stage.')
            graph=self.payload['graph'];self.graphs.append(graph_record(graph))
            small=graph.subgraph([n for n in graph if len(graph[n])<100])
            day=dict(phase=row['phase'],author_day=p['day'],date=self.dates[p['day']].date().isoformat(),
                     edges=graph.number_of_edges(),weak_ties=len(list(nx.local_bridges(small,with_span=False))),
                     clustering=nx.average_clustering(graph),components=nx.number_connected_components(small),
                     graph_sha256=digest(graph_record(graph)))
            self.days.append(day);row['completed_day']=day
        return row

    def finish(self):
        if self.round!=1764:raise ValueError('Full configuration requires all 1764 stages.')
        try:self.prepare(1765)
        except StopIteration:return
        raise AssertionError('The source unexpectedly has another stage.')

    def checkpoint(self):
        return dict(stage_number=self.round,phase=self.phase,days_completed=len(self.days),score_count=self.score_count,
            selected_count=self.selected_count,current_memory=memory_record(self.obj.mem_dict) if self.obj else memory_record(self.memory),
            shared_prefix_memory=memory_record(self.prefix) if self.prefix is not None else None,
            rng=dict(name=self.rng[0],keys=self.rng[1].tolist(),position=self.rng[2],has_gauss=self.rng[3],cached_gaussian=self.rng[4]),
            reconstruction='Generator resumed by exact journal reexecution from the original initial state; checkpoint is inspectable, not a pickled generator.')


class NativeProbabilityEngine:
    def __init__(self,world):self.world=world
    def decide(self,state,questions):
        return {q:{'contact':float(p),'not_contact':1-float(p)} for q,p in zip(questions,self.world.pending[0]['native_probabilities'])}
    def usage(self):return dict(actual_api_calls=0,engine='untouched-source-relative-weights')
