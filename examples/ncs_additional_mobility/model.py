"""Native PedNav path generation inside ORDO; independent trips, not coupled ABM."""
import ast
import hashlib
import io
import json
from pathlib import Path
import pickle
import types
import warnings

import numpy as np

from orgabm.sdk import DecisionBatch,FunctionEngine
from .sources import DEFAULT,FILES,DOI,COMMIT


def graph_library():
    try:import igraph
    except ImportError as error:raise ImportError('Install the optional PedNav dependency: python -m pip install igraph==0.11.9') from error
    return igraph


class NumericGraphUnpickler(pickle.Unpickler):
    def find_class(self,module,name):
        ig=graph_library()
        if (module,name)==('igraph','Graph'):return ig.Graph
        if module in ('numpy.core.multiarray','numpy._core.multiarray') and name in ('_reconstruct','scalar'):
            return getattr(np._core.multiarray,name)
        if module=='numpy' and name in ('ndarray','dtype'):return getattr(np,name)
        raise pickle.UnpicklingError('Unapproved public-data constructor: '+module+'.'+name)
    def persistent_load(self,pid):raise pickle.UnpicklingError('External archive references are disabled.')


def restricted_load(stream,**kwargs):
    return NumericGraphUnpickler(stream,encoding=kwargs.get('encoding','latin1')).load()


def pinned(path,sha):
    raw=Path(path).read_bytes()
    if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=sha:
        raise ValueError('Author file differs from the declared version.')
    return raw


class AuthorNavigation:
    def __init__(self,cache=DEFAULT):
        self.cache=Path(cache);ig=graph_library()
        for name,(sha,size) in FILES.items():pinned(self.cache/name,sha)
        code=(self.cache/'pednav/main.py').read_text(encoding='utf-8')
        tree=ast.parse(code);classes=[node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='Navigation']
        if len(classes)!=1:raise ValueError('Expected author Navigation class.')
        namespace=dict(np=np,ig=ig,pk=types.SimpleNamespace(load=restricted_load))
        exec(compile(ast.Module(body=classes,type_ignores=[]),'pinned_pednav_navigation','exec'),namespace)
        self.navigation=namespace['Navigation'](str(self.cache/'data/graph_clusters_30m_bos.pk'))
        with (self.cache/'data/Human_Paths_bos.pk').open('rb') as stream:human=restricted_load(stream)
        if not isinstance(human,dict) or len(human)!=100:raise ValueError('Expected the public 100-trip Boston sample.')
        self.human=[]
        for key,path in human.items():
            values=[int(x) for x in path]
            if len(values)<2 or any(not 0<=x<self.navigation.g.vcount() for x in values):raise ValueError('Invalid public trip.')
            self.human.append(dict(id=str(key),path=values,origin=values[0],destination=values[-1]))
        self.graph_sha256=hashlib.sha256((self.cache/'data/graph_clusters_30m_bos.pk').read_bytes()).hexdigest()
    def route(self,kind,origin,destination,sigma,seed):
        if kind not in ('vector','shortest'):raise ValueError('Unknown author navigation model.')
        if type(seed) is not int or not 0<=seed<2**32:raise ValueError('Invalid route seed.')
        old=np.random.get_state()
        try:
            np.random.seed(seed)
            with np.errstate(divide='ignore',invalid='ignore'):
                fn=self.navigation.Stochastic_Vector_Path if kind=='vector' else self.navigation.Stochastic_Shortest_Path
                route=fn(destination,[origin],sigma)[0]
            return [int(x) for x in route]
        finally:np.random.set_state(old)
    def describe(self):
        g=self.navigation.g
        return dict(doi=DOI,author_commit=COMMIT,graph='author public Boston pedestrian network',
            vertices=g.vcount(),edges=g.ecount(),graph_sha256=self.graph_sha256,public_human_trips=len(self.human))
    def route_metrics(self,route,origin,destination):
        g=self.navigation.g
        if not route or route[0]!=origin or route[-1]!=destination:raise AssertionError('Route has incorrect endpoints.')
        pairs=list(zip(route,route[1:]));ids=g.get_eids(pairs=pairs,directed=False,error=True) if pairs else []
        length=sum(g.es[i]['weight'] for i in ids)
        shortest=float(g.distances(origin,destination,weights='weight')[0][0])
        return dict(nodes=len(route),length_m=float(length),shortest_length_m=shortest,
            detour_ratio=float(length)/shortest if shortest else 1.0,
            path_sha256=hashlib.sha256(json.dumps(route,separators=(',',':')).encode()).hexdigest())


class PedNavTrips:
    def __init__(self,author,kind='vector',sigma=.7,seed=7,trip_limit=20):
        if kind not in ('vector','shortest') or type(sigma) not in (int,float) or not 0<=sigma<=3:
            raise ValueError('Use vector/shortest and sigma in [0,3].')
        if type(seed) is not int or not 0<=seed<2**32:raise ValueError('Invalid seed.')
        if type(trip_limit) is not int or not 1<=trip_limit<=len(author.human):raise ValueError('Choose 1..100 public trips.')
        self.author=author;self.kind=kind;self.sigma=sigma;self.seed=seed;self.trips=author.human[:trip_limit]
        self.round=0;self.pending=False;self.routes=[];self.trajectory=[]
    def describe(self):
        return dict(scenario='ncs_pednav_native_component',**self.author.describe(),kind=self.kind,sigma=self.sigma,
            seed=self.seed,trip_count=len(self.trips),scope='Fresh native route samples for independent trips, not interacting population ABM or new Jev inference.',
            source_changes='Unmodified author Navigation class; restricted graph loader; explicit per-trip NumPy seeds with state restoration.')
    def prepare(self,t):
        if self.pending or t!=self.round+1 or t>len(self.trips):raise ValueError('Finish the prior trip.')
        self.pending=True;trip=self.trips[t-1];qid=f'trip-{t}'
        return DecisionBatch('Commit one independent pedestrian trip using the declared native routing mechanism.',
            {qid:dict(type='choice',instructions=json.dumps({k:trip[k] for k in ('id','origin','destination')}),
                criteria={'native_route':'Generate and commit one path using the unchanged author navigation model.'})},
            {qid:t-1})
    def advance(self,t,actions,probabilities):
        if not self.pending or t!=self.round+1 or actions!={f'trip-{t}':'native_route'}:raise ValueError('Invalid native trip commit.')
        trip=self.trips[t-1];route=self.author.route(self.kind,trip['origin'],trip['destination'],self.sigma,(self.seed+t-1)%2**32)
        row=dict(trip=t,id=trip['id'],origin=trip['origin'],destination=trip['destination'],
            **self.author.route_metrics(route,trip['origin'],trip['destination']))
        self.routes.append(route);self.trajectory.append(row);self.round=t;self.pending=False;return row


def native_engine():return FunctionEngine(lambda state,q:{'native_route':1.0},name='author-native-route-controller')
