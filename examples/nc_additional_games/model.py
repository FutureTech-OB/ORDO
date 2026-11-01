"""Author-native reputation/reward evolution via the ordinary ORDO SDK.

Pal & Hilbe (2022), Nature Communications 13:5928.
MIT author source and notice are retained in upstream/.
"""
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import numpy as np
from orgabm.sdk import DecisionBatch

COMMIT='e26e00516c8448a951e25dd6ef388e4eb188f41c'
DOI='10.1038/s41467-022-33551-y'
REPO='https://github.com/Saptarshi07/social-rewarding'
SOURCE=Path(__file__).parent/'upstream'/'author_social_rewarding.py'
BLOB='7723518b117b89ff7e33a20c527b217337d8ed92'
DONORS=['C','OC','OD','D'];REWARDERS=['NR','SR','AR','UR']


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def source_manifest():
    raw=SOURCE.read_bytes().replace(b'\r\n',b'\n')
    actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if actual!=BLOB:raise ValueError('Pinned author source changed.')
    return dict(url=REPO+'/blob/'+COMMIT+'/two-player/reward_simuls.py',commit=COMMIT,
        git_blob_sha=actual,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
        compatibility='random.sample(set,1) converted to random.sample(list(set),1) for Python >=3.11; same iteration order, no sorting.')


class SampleCompatibility(ast.NodeTransformer):
    def visit_Call(self,node):
        self.generic_visit(node)
        if (isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='random'
            and node.func.attr=='sample' and node.args and isinstance(node.args[0],ast.Name) and node.args[0].id=='stg_removed'):
            node.args[0]=ast.Call(func=ast.Name(id='list',ctx=ast.Load()),args=[node.args[0]],keywords=[])
        return node


def author_namespace(config):
    source_manifest();tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
    ns=dict(np=np,math=math,random=random.Random(config['seed']),pop=config['agents'],pops=range(1,config['agents']+1),
        lmd=config['information'],b=config['benefit'],c=config['cost'],beta=config['reward'],gamma=config['reward_cost'],
        mu=config['mutation'],s=config['selection'],strategy_set=[(i,j) for i in range(4) for j in range(4)])
    defs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
    exec(compile(ast.Module(body=defs,type_ignores=[]),'pinned_rewarding_functions','exec'),ns)
    ns['payoff_A'],ns['payoff_B']=ns['get_payoff'](ns['b'],ns['c'],ns['beta'],ns['gamma'],ns['lmd'])
    loop=next(n for n in tree.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='t')
    body=[]
    for statement in loop.body:
        if isinstance(statement,ast.With):continue
        if isinstance(statement,ast.Expr) and isinstance(statement.value,ast.Call) and isinstance(statement.value.func,ast.Name) and statement.value.func.id=='print':continue
        if isinstance(statement,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='data' for x in statement.targets):continue
        statement=copy.deepcopy(statement)
        if isinstance(statement,ast.If):
            statement.body.insert(0,ast.Assign(targets=[ast.Name(id='mutated',ctx=ast.Store())],value=ast.Constant(True)))
            statement.orelse.insert(0,ast.Assign(targets=[ast.Name(id='mutated',ctx=ast.Store())],value=ast.Constant(False)))
        body.append(statement)
    wrapper=ast.parse('def step(donor_behav,recep_behav):\n    pass').body[0]
    wrapper.body=body+ast.parse('return stgs,coop_rate,focul,rolemodel,mutated').body
    module=SampleCompatibility().visit(ast.Module(body=[wrapper],type_ignores=[]));ast.fix_missing_locations(module)
    exec(compile(module,'pinned_rewarding_update','exec'),ns)
    return ns


def initialize(ns,n):
    donor={i:0 for i in range(1,n+1)};recipient=dict(donor)
    D=[i for i in range(4) for _ in range(n//4)];R=list(D)
    ns['random'].shuffle(D);ns['random'].shuffle(R)
    for i in range(1,n+1):donor[i]=D.pop();recipient[i]=R.pop()
    return donor,recipient


def state_hash(donor,recipient):return digest([donor,recipient])


class SocialRewarding:
    def __init__(self,*,agents=100,rounds=3000,information=.5,mutation=.01,selection=1,benefit=4,cost=1,reward=3,reward_cost=1,seed=7):
        if type(agents) is not int or agents<4 or agents%4 or agents>10000:raise ValueError('Use a population divisible by four in 4..10,000.')
        if type(rounds) is not int or not 1<=rounds<=1_000_000:raise ValueError('Invalid update horizon.')
        if not 0<=information<=1 or not 0<=mutation<=1 or not 0<=selection<=10:raise ValueError('Invalid evolution parameters.')
        self.config=dict(agents=agents,rounds=rounds,information=information,mutation=mutation,selection=selection,
            benefit=benefit,cost=cost,reward=reward,reward_cost=reward_cost,seed=seed)
        self.ns=author_namespace(self.config);self.donor,self.recipient=initialize(self.ns,agents)
        self.round=0;self.pending=None
    def describe(self):
        return dict(model='nc_reputation_social_rewarding',doi=DOI,commit=COMMIT,**self.config,
            timing='one randomly selected focal strategy update; mutation or payoff-based imitation',
            information_scope='analytic well-mixed payoff, no personal memory or learned textual reasoning')
    def prepare(self,t):
        if t!=self.round+1 or self.pending is not None:raise ValueError('Finish the preceding update.')
        shadow_d=copy.deepcopy(self.donor);shadow_r=copy.deepcopy(self.recipient)
        counts,cooperation,focal,partner,mutated=self.ns['step'](shadow_d,shadow_r)
        own=4*self.donor[focal]+self.recipient[focal];candidate=4*self.donor[partner]+self.recipient[partner]
        allowed=[i for i in range(16) if i!=own] if mutated else sorted({own,candidate})
        native=4*shadow_d[focal]+shadow_r[focal]
        self.pending=dict(focal=focal,native=native,allowed=allowed,pre_counts=counts,pre_cooperation=cooperation,
            partner=partner,mutation=mutated,proposed_state_sha256=state_hash(shadow_d,shadow_r))
        question=dict(type='choice',instructions=json.dumps(dict(own_strategy=own,rolemodel_strategy=candidate,
            mutation=mutated,information=self.config['information'],selection=self.config['selection'])),
            criteria={str(i):DONORS[i//4]+','+REWARDERS[i%4] for i in allowed})
        qid=f't{t}_a{focal}'
        return DecisionBatch('Native social-reward strategy update: donor behavior and recipient rewarding policy.',{qid:question},{qid:focal})
    def advance(self,t,actions,probabilities):
        focal=self.pending['focal'];qid=f't{t}_a{focal}';strategy=int(actions[qid])
        if strategy not in self.pending['allowed']:raise ValueError('Strategy outside this event\'s feasible set.')
        self.donor[focal]=strategy//4;self.recipient[focal]=strategy%4;self.round=t
        counts=self.ns['get_stg_dist'](self.donor,self.recipient)
        metric=dict(update=t,focal=focal,mutation=self.pending['mutation'],strategy=strategy,
            pre_strategy_counts=self.pending['pre_counts'],pre_cooperation=self.pending['pre_cooperation'],
            post_strategy_counts=counts,post_cooperation=self.ns['get_coop_rate'](counts),
            social_rewarding_share=sum(counts[i] for i in (1,5,9,13))/self.config['agents'],
            state_sha256=state_hash(self.donor,self.recipient))
        self.pending=None;return metric
    def snapshot(self):return dict(donor=self.donor,recipient=self.recipient,round=self.round)


class NativeEngine:
    def __init__(self,world):self.world=world
    def decide(self,state,questions):
        value=str(self.world.pending['native'])
        return {qid:{a:float(a==value) for a in q['criteria']} for qid,q in questions.items()}
    def usage(self):return dict(engine='pinned-author-mutation-imitation',actual_model_api_calls=0,recorded_input_cost_usd=0)


def direct_reference(config):
    ns=author_namespace(config);donor,recipient=initialize(ns,config['agents']);rows=[]
    for t in range(1,config['rounds']+1):
        pre_counts,pre_cooperation,focal,partner,mutated=ns['step'](donor,recipient)
        counts=ns['get_stg_dist'](donor,recipient)
        rows.append(dict(state_sha256=state_hash(donor,recipient),pre_strategy_counts=pre_counts,
            pre_cooperation=pre_cooperation,post_strategy_counts=counts,post_cooperation=ns['get_coop_rate'](counts)))
    return rows
