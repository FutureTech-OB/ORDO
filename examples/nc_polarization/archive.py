"""Strictly limited decoding of hash-pinned numeric pandas snapshots."""
import importlib
import io
import math
import pickle
from pathlib import Path

import numpy as np


class NumericSnapshotUnpickler(pickle.Unpickler):
    allowed={('pandas.core.frame','DataFrame'),('pandas','DataFrame'),('pandas.core.internals.managers','BlockManager'),
        ('pandas._libs.internals','_unpickle_block'),('numpy.core.multiarray','_reconstruct'),
        ('numpy._core.multiarray','_reconstruct'),('numpy','ndarray'),('numpy','dtype'),
        ('builtins','slice'),('pandas.core.indexes.base','_new_Index'),
        ('pandas.core.indexes.base','Index'),('pandas.core.indexes.range','RangeIndex'),
        ('pandas','Index'),('pandas','RangeIndex')}
    def find_class(self,module,name):
        if (module,name) not in self.allowed:raise pickle.UnpicklingError('Unapproved archive constructor: '+module+'.'+name)
        return getattr(importlib.import_module(module),name)
    def persistent_load(self,pid):raise pickle.UnpicklingError('External archive references are disabled.')


def load_snapshot(path,population=1000):
    raw=Path(path).read_bytes()
    if len(raw)>1_000_000:raise ValueError('Snapshot exceeds the declared numeric fixture size.')
    frame=NumericSnapshotUnpickler(io.BytesIO(raw)).load()
    columns=['source node Id','target node Id','source node state','target node state']
    if type(frame).__name__!='DataFrame' or len(frame.columns)!=4 or set(frame.columns)!=set(columns):
        raise ValueError('Unexpected snapshot schema.')
    if not 1<=len(frame)<=10000:raise ValueError('Unexpected edge count.')
    states={};edges=[]
    def integer(value):
        n=float(value)
        if not math.isfinite(n) or n!=int(n):raise ValueError('Nonintegral node/state value.')
        return int(n)
    for source,target,s,t in frame[columns].itertuples(index=False,name=None):
        source,target,s,t=map(integer,(source,target,s,t))
        if not 0<=source<population or not 0<=target<population or s not in range(-2,3) or t not in range(-2,3):
            raise ValueError('Invalid node or opinion.')
        for actor,state in ((source,s),(target,t)):
            if actor in states and states[actor]!=state:raise ValueError('Conflicting opinion observations for one snapshot.')
            states[actor]=state
        edges.append((source,target))
    if set(states)!=set(range(population)):raise ValueError('Snapshot does not identify every member state.')
    return dict(states=[states[i] for i in range(population)],edges=[list(e) for e in edges])


def metrics(snapshot):
    states=snapshot['states'];edges=snapshot['edges'];n=len(states)
    count={str(s):states.count(s) for s in range(-2,3)}
    return dict(population=n,edges=len(edges),unique_edges=len({tuple(e) for e in edges}),
        duplicate_edge_rows=len(edges)-len({tuple(e) for e in edges}),self_edge_rows=sum(a==b for a,b in edges),counts=count,neutral_share=count['0']/n,
        mean_opinion=sum(states)/n,polarization=sum(abs(x) for x in states)/n,
        exact_opinion_homophily=sum(states[a]==states[b] for a,b in edges)/len(edges),
        same_sign_homophily=float(sum(np.sign(states[a])==np.sign(states[b]) for a,b in edges)/len(edges)))
