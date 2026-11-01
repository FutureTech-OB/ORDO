"""ORDO environment adapter for the author's native communication-network kernel."""
from copy import deepcopy
import hashlib
import json
import networkx as nx
import numpy as np
from orgabm.sdk import DecisionBatch, FunctionEngine
from .sources import author_class, dataset, PARAMETERS


def canonical_graph(graph):
    return dict(nodes=sorted(graph.nodes), edges=sorted(tuple(sorted(e)) for e in graph.edges))


def state_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def memory_state(memory):
    return [[list(e), days] for e, days in sorted(memory.items())]


def phases(policy, lengths):
    if policy not in ('continuous_colocation', 'remote_then_return'):
        raise ValueError('Unknown co-location policy.')
    return [(lengths[0], False), (lengths[1], policy == 'remote_then_return'), (lengths[2], False)]


class ColocationEnvironment:
    """The author kernel owns coupled edge draws; SDK advances one complete day.

    Native draws are intentionally not split into independent Bernoulli choices:
    each day has two weighted samples *without replacement*. This adapter tests
    native environment integration, not the external DecisionEngine pathway.
    """
    def __init__(self, root, *, population=100, seed=7, policy='remote_then_return', lengths=(10,15,10)):
        if not 80 <= population <= 501 or len(lengths) != 3 or any(type(n) is not int or n<1 for n in lengths):
            raise ValueError('Use 80..501 public-demo nodes and three positive phase lengths.')
        self.root=root; self.population=population; self.seed=seed; self.policy=policy; self.lengths=tuple(lengths)
        self.nodes,self.distances,self.dates,self.memory=dataset(root,population)
        self.cls,self.transformed_sha=author_class(root,self.distances,self.dates,daily=True)
        self.day=10; self.round=0; self.phase=-1; self.phase_left=0; self.current=None
        self.rng_state=np.random.RandomState(seed).get_state()
        self.records=[]; self.graphs=[]; self.pending=False; self.native_edge_draws=0

    def describe(self):
        return dict(scenario='organizational_colocation_network',doi='10.1038/s43588-022-00296-z',
                    population=self.population,seed=self.seed,policy=self.policy,phase_days=self.lengths,
                    public_demo=True,native_environment=True,external_decisions=False,
                    native_rule='Two weighted edge samples without replacement per day; native graph memory and closure.',
                    transformations=['One yield appended after the original complete-day loop body.',
                                     'Available initial edge dictionary sorted to stabilize process-independent order.'],
                    compatibility='Original estimator bases stubbed; trange replaced by range; author weekday convention retained.')

    def prepare(self,t):
        if self.pending or t!=self.round+1:raise ValueError('Commit each complete native day before preparing another.')
        self.pending=True
        return DecisionBatch('Published native organizational-network transition; no external decision request.',{}, {})

    def advance(self,t,actions,probabilities):
        if not self.pending or actions or probabilities:raise ValueError('This native environment has no external choices.')
        global_rng=np.random.get_state()
        try:
            np.random.set_state(self.rng_state)
            if self.phase_left==0:
                self.phase+=1
                n,remote=phases(self.policy,self.lengths)[self.phase]
                distances={e:(2000,v[1]) for e,v in self.distances.items()} if remote else self.distances
                self.current=self.cls(self.memory,distances,**PARAMETERS)
                self.iterator=self.current.transform(None,start=self.day,end=self.day+n)
                self.phase_left=n
            graph=next(self.iterator)
            self.memory=self.current.mem_dict
            self.rng_state=np.random.get_state()
        finally:
            np.random.set_state(global_rng)
        self.phase_left-=1;self.day+=1;self.round=t;self.pending=False
        serialized=canonical_graph(graph);self.graphs.append(serialized)
        small=graph.subgraph([v for v in graph if len(graph[v])<100])
        edges=set(map(tuple,serialized['edges']))
        previous=set(map(tuple,self.graphs[-6]['edges'])) if len(self.graphs)>=6 else None
        metrics=dict(round=t,day=self.day-1,phase=self.phase,population=self.population,
                     edges=len(edges),weak_ties=len(list(nx.local_bridges(small,with_span=False))),
                     components=nx.number_connected_components(small),clustering=nx.average_clustering(graph),
                     weekly_iou=len(edges & previous)/len(edges | previous) if previous is not None else None,
                     graph_sha256=state_hash(serialized),memory_sha256=state_hash(memory_state(self.memory)))
        self.native_edge_draws+=len(edges);self.records.append(metrics)
        if self.phase_left==0:
            # Exhaust original post-loop merge code and return path as well.
            try:next(self.iterator)
            except StopIteration:pass
            else:raise AssertionError('Native phase produced an extra day.')
        return metrics

    def snapshot(self):
        return dict(graphs=self.graphs,memory=memory_state(self.memory),records=self.records)


def native_engine():
    return FunctionEngine(lambda state,q:{},name='native-environment-no-external-decisions')


def reference(root,*,population,seed,policy,lengths):
    """Independent execution of the unmodified original transform, full phase calls."""
    _,distances,dates,memory=dataset(root,population)
    cls,_=author_class(root,distances,dates,daily=False)
    saved=np.random.get_state();np.random.seed(seed)
    day=10;graphs=[];weak=[];components=[];phase_memories=[]
    try:
        for n,remote in phases(policy,lengths):
            dist={e:(2000,v[1]) for e,v in distances.items()} if remote else distances
            obj=cls(memory,dist,**PARAMETERS)
            bridges,comps,simulated=obj.transform(None,start=day,end=day+n)
            graphs.extend(canonical_graph(g) for g in simulated)
            weak.extend(bridges.tolist());components.extend(comps.tolist())
            memory=obj.mem_dict;day+=n
            phase_memories.append(state_hash(memory_state(memory)))
    finally:np.random.set_state(saved)
    return dict(graphs=graphs,weak_ties=weak,components=components,
                memory=memory_state(memory),phase_memory_sha256=phase_memories)
