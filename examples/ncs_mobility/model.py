"""ORDO scheduling adapter around the author's native CMM kernel.

One SDK action commits one native period; per-person decisions remain native.
This adapter does not claim Jev replacement of mobility choices.
"""
from collections import Counter
import ctypes
import hashlib
import json
import math
from pathlib import Path

from orgabm.sdk import DecisionBatch,FunctionEngine
from .build import DEFAULT


def digest(value):
    return hashlib.sha256(json.dumps(value,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def decode_state(values):
    t,n=values[:2];cursor=2;arrays=[]
    for mode in range(3):
        count=values[cursor];cursor+=1;row={}
        for i in range(count):
            index,value=values[cursor:cursor+2];cursor+=2
            if value>=2**63:value-=2**64
            row[index]=value
        arrays.append(row)
    agents=[]
    for i in range(n):
        pos,visited,times,seed=values[cursor:cursor+4];cursor+=4
        history=[]
        for j in range(visited):history.append(values[cursor:cursor+2]);cursor+=2
        agents.append(dict(position=pos,visited=visited,times=times,rng=seed,visitation_frequencies=history))
    if cursor!=len(values):raise ValueError('Native snapshot layout differs.')
    return dict(period=t,agents=agents,frozen_population=arrays[0],pre_population=arrays[1],pending_flow=arrays[2])


def metrics(values,config):
    state=decode_state(values);n=config['agents'];positions=Counter(a['position'] for a in state['agents'])
    frozen=state['frozen_population'];flow=state['pending_flow']
    if sum(positions.values())!=n or sum(frozen.values())!=n or sum(flow.values())!=0:
        raise AssertionError('Native population mass changed.')
    if any(frozen.get(i,0)+flow.get(i,0)!=positions.get(i,0) for i in set(frozen)|set(flow)|set(positions)):
        raise AssertionError('Pending movement ledger differs from actual positions.')
    if config['memory'] and any(sum(f for _,f in a['visitation_frequencies'])!=a['times'] for a in state['agents']):
        raise AssertionError('Individual visitation memory is not conserved.')
    radii=[]
    for a in state['agents']:
        x,y=a['position']%300,a['position']//300
        dx=min(abs(x-150),300-abs(x-150));dy=min(abs(y-150),300-abs(y-150))
        radii.append(math.hypot(dx,dy))
    return dict(period=state['period'],population=n,native_agent_updates=n,occupied_sites=len(positions),
        mean_memory_locations=sum(a['visited'] for a in state['agents'])/n,
        mean_toroidal_radius=sum(radii)/n,spatial_concentration=sum((v/n)**2 for v in positions.values()),
        population_mass=n,pending_flow_mass=sum(flow.values()),state_sha256=digest(values))


def validate(config):
    result={**dict(agents=128,rounds=40,seed=7,memory=True,rho0=1e-12),**config}
    if set(result)!={'agents','rounds','seed','memory','rho0'}:raise ValueError('Unknown CMM configuration field.')
    if type(result['agents']) is not int or not 1<=result['agents']<=2000:raise ValueError('Use 1..2,000 agents for this bounded cookbook.')
    if type(result['rounds']) is not int or not 1<=result['rounds']<=1000:raise ValueError('Use 1..1,000 periods.')
    if type(result['seed']) is not int or not 0<=result['seed']<2**31:raise ValueError('Use a nonnegative signed-32-bit seed.')
    if type(result['memory']) is not bool:raise ValueError('Memory must be boolean.')
    if type(result['rho0']) not in (int,float) or not math.isfinite(result['rho0']) or result['rho0']<0:
        raise ValueError('rho0 must be finite and nonnegative.')
    return result


class NativeMobility:
    _active=False
    def __init__(self,config,build_root=DEFAULT):
        if NativeMobility._active:
            raise RuntimeError('The author kernel has process-global state; close the active environment or use another process.')
        self.config=validate(config);self.root=Path(build_root).resolve();self.round=0
        self.provenance=json.loads((self.root/'build_manifest.json').read_text(encoding='utf-8'))
        if hashlib.sha256((self.root/'cmm_bridge.dll').read_bytes()).hexdigest()!=self.provenance['cmm_bridge.dll']:
            raise ValueError('Native library differs from its declared build.')
        self.dll=ctypes.CDLL(str(self.root/'cmm_bridge.dll'))
        self.dll.cmm_init.argtypes=[ctypes.c_int,ctypes.c_uint,ctypes.c_int,ctypes.c_double]
        self.dll.cmm_copy_state.argtypes=[ctypes.POINTER(ctypes.c_uint64),ctypes.c_int]
        if self.dll.cmm_init(self.config['agents'],self.config['seed'],int(self.config['memory']),self.config['rho0'])<0:
            raise ValueError('Native initialization rejected.')
        NativeMobility._active=True;self.closed=False
        self.pending=False;self.final_values=None
    def describe(self):
        return dict(scenario='ncs_collective_mobility_native',config=self.config,
            source_doi='10.1038/s43588-021-00160-6',author_commit=self.provenance['commit'],
            source_sha256=self.provenance['source_sha256'],generated_bridge_sha256=self.provenance['generated_sha256'],
            scope='Reduced author-kernel execution and ORDO scheduling equivalence, not full published urban-scaling replication.',
            engine_scope='One control action per period; individual mobility decisions remain in the native author kernel.',
            scheduling='Frozen prior-period population; native agents stepped serially with per-agent RNG; pending movement flushed at next period.',
            fixed=dict(lattice_side=300,delta=1,gamma=.21,alpha=-2.55),patches=self.provenance['patches'])
    def prepare(self,t):
        if self.pending or t!=self.round+1:raise ValueError('Finish the prior period before preparation.')
        self.pending=True;qid=f'period-{t}'
        return DecisionBatch('Commit one native CMM period without replacing the author mobility rule.',
            {qid:dict(type='choice',instructions='Advance the pinned author kernel by one complete period.',criteria={'native_step':'Run native period.'})},
            {qid:'native-kernel-controller'})
    def advance(self,t,actions,probabilities):
        if not self.pending or t!=self.round+1 or actions!={f'period-{t}':'native_step'}:raise ValueError('Invalid native period commit.')
        if self.dll.cmm_step()!=t:raise RuntimeError('Native kernel could not advance.')
        size=self.dll.cmm_state_size();buffer=(ctypes.c_uint64*size)()
        if self.dll.cmm_copy_state(buffer,size)!=size:raise RuntimeError('Native state export failed.')
        self.final_values=list(buffer);self.round=t;self.pending=False
        return metrics(self.final_values,self.config)
    def close(self):
        if not self.closed:
            self.dll.cmm_close();self.closed=True;NativeMobility._active=False


def native_engine():
    return FunctionEngine(lambda state,q:{'native_step':1.0},name='native-author-kernel-controller')
