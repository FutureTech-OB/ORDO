"""Reuse author strategy classes while keeping the ORDO interaction contract.

Source: Su et al., Nature Communications 17:490 (2026),
DOI 10.1038/s41467-025-67178-6. The original MIT notice is in upstream/.
The source's top-level plotting, file I/O and large loops are never executed.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
import random
import warnings
import numpy as np

from orgabm.sdk import DecisionBatch


REPO='https://github.com/YuzukiWang/multiagent_q_learning_for_evolutionary_games'
COMMIT='3e3c3bf2bc50761acabd7a42a785dac0e15f3f84'
DOI='10.1038/s41467-025-67178-6'
SOURCES={
    'author_payoff.py':('simulation_code/Fig2/generate_payoff_heatmap.py','32637461a04ee1d513f8b1c8e8246a32f3dfaaa7'),
    'author_well_mixed.py':('simulation_code/Fig4&FigS5&FigS6/Well-mixed.py','9c24ef29b7dc019e320dac46d417943acff555d8'),
    'strategy0729.json':('Fig2&FigS2/strategy0729.txt','bdf32c9080214edeb58a35a124b5857a36fd7edf')}
# Approved comment-only English variant; upstream source identity remains in SOURCES.
ENGLISH_COMMENT_VARIANTS={'author_well_mixed.py':'f1504ea1819161f707e0b6e4cbde2975daf606c2'}
NAMES={-1:'MTBR',0:'TFT',1:'GTFT',2:'WSLS',3:'Grudge',4:'FoolMeOnce',5:'OmegaTFT',6:'GradualTFT',15:'AllD'}
STATE='Repeated simultaneous two-action game. C=cooperate (source action 0); D=defect (source action 1). Own history rows are [opponent action,own action].'


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def source_manifest():
    rows=[]
    for local,(remote,expected) in SOURCES.items():
        raw=(Path(__file__).parent/'upstream'/local).read_bytes()
        blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        # Vendored files are source bytes. LF-normalization permits normal Git checkouts.
        if blob!=expected:
            raw=raw.replace(b'\r\n',b'\n')
            blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if blob not in (expected,ENGLISH_COMMENT_VARIANTS.get(local)):
            raise ValueError('Pinned author source changed: '+local)
        rows.append(dict(file=local,url=REPO+'/blob/'+COMMIT+'/'+remote,git_blob_sha=blob,
                         sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
                         upstream_git_blob_sha=expected,
                         adaptation=('English comments; executable AST unchanged' if blob!=expected else None)))
    return rows


def author_namespace(seed):
    source_manifest()
    text=(Path(__file__).parent/'upstream'/'author_payoff.py').read_text(encoding='utf-8')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',SyntaxWarning)
        tree=ast.parse(text)
    definitions=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name in ('AgentQ','AgentDefined')]
    if {n.name for n in definitions}!={'AgentQ','AgentDefined'}:raise ValueError('Author strategy definitions unavailable.')
    namespace=dict(np=np,random=random.Random(seed),R=3,S=0,T=5,P=1)
    # Reviewed, hash-pinned local definitions only. No source top-level statements.
    exec(compile(ast.Module(body=definitions,type_ignores=[]),'pinned_author_strategy_classes','exec'),namespace)
    table=json.loads((Path(__file__).parent/'upstream'/'strategy0729.json').read_text(encoding='utf-8'))
    namespace['q_table']=dict(table)
    return namespace


def make_player(namespace,strategy):
    if strategy not in NAMES:raise ValueError('Unsupported strategy identifier.')
    if strategy==-1:
        player=namespace['AgentQ'](2);player.Q=copy.deepcopy(namespace['q_table']);return player
    return namespace['AgentDefined'](strategy)


def rewards(a,b):
    return ((3,3),(0,5),(5,0),(1,1))[2*a+b]


class RepeatedGame:
    def __init__(self,strategies=(-1,-1),initial=(0,1),rounds=20,seed=7):
        if len(strategies)!=2 or any(s not in NAMES for s in strategies):raise ValueError('Select two supported strategies.')
        if len(initial)!=2 or any(a not in (0,1) for a in initial):raise ValueError('Initial actions must be zero/one.')
        if type(rounds) is not int or not 1<=rounds<=1000:raise ValueError('Use 1..1,000 repeated rounds.')
        self.strategies=list(strategies);self.initial=list(initial);self.rounds=rounds;self.seed=seed
        self.histories=[[],[]];self.scores=[0,0];self.round=0;self.actions=[]
    def describe(self):
        return dict(model='nc_repeated_game_evaluation',doi=DOI,commit=COMMIT,
            strategies=[NAMES[s] for s in self.strategies],first_move_flags=self.initial,rounds=self.rounds,
            timing='both decisions before both history/payoff updates',scope='evaluation of supplied trained strategy; no retraining')
    def prepare(self,t):
        if t!=self.round+1:raise ValueError('Round order changed.')
        questions={}
        for i in (0,1):
            questions[f't{t}_a{i}']=dict(type='choice',instructions=json.dumps(dict(player=i,
                strategy=NAMES[self.strategies[i]],first_move_flag=self.initial[i] if t==1 else None,
                history=self.histories[i],payoff=self.scores[i])),criteria={'C':'Cooperate','D':'Defect'})
        return DecisionBatch(STATE,questions,{q:i for i,q in enumerate(questions)})
    def advance(self,t,actions,probabilities):
        values=[int(actions[f't{t}_a{i}']=='D') for i in (0,1)]
        if any(a not in ('C','D') for a in actions.values()):raise ValueError('Invalid source action.')
        payoff=rewards(*values)
        self.histories[0].append([values[1],values[0]]);self.histories[1].append([values[0],values[1]])
        self.scores=[s+p for s,p in zip(self.scores,payoff)];self.actions.append(values);self.round=t
        return dict(round=t,actions=values,payoffs=list(payoff),scores=list(self.scores),
            cooperation=sum(1-a for row in self.actions for a in row)/(2*t),state_sha256=digest(self.snapshot()))
    def snapshot(self):
        return dict(round=self.round,histories=self.histories,scores=self.scores,actions=self.actions)


class AuthorStrategyEngine:
    """One-hot outputs preserve the original author's random draw stream exactly."""
    def __init__(self,world):
        self.namespace=author_namespace(world.seed);self.players=[make_player(self.namespace,s) for s in world.strategies]
        self.initial=world.initial
    def decide(self,state,questions):
        result={}
        for qid,q in questions.items():
            record=json.loads(q['instructions']);i=record['player']
            value=self.players[i].pick_action(record['history'],self.initial[i]==0)
            if value not in (0,1):raise ValueError('Original strategy did not return an action.')
            result[qid]={'C':float(value==0),'D':float(value==1)}
        return result
    def usage(self):return dict(engine='author-strategy-classes',actual_model_api_calls=0,recorded_input_cost_usd=0)


def direct_reference(strategies,initial,rounds,seed):
    """Independent straight-line loop following author's original pair evaluation."""
    ns=author_namespace(seed);p1,p2=[make_player(ns,s) for s in strategies]
    state1=[];state2=[];score1=score2=0;actions=[];states=[]
    for t in range(1,rounds+1):
        # NumPy 2 scalar repr differs from the source's NumPy 1.24 string keys.
        # Canonical binary action ints preserve the old history-key semantics.
        a=int(p1.pick_action(state1,initial[0]==0));b=int(p2.pick_action(state2,initial[1]==0))
        state1.append([b,a]);state2.append([a,b]);actions.append([int(a),int(b)])
        # Same explicit payoff cases as the original evaluation loop.
        if a==0 and b==0:r1,r2=3,3
        elif a==0 and b==1:r1,r2=0,5
        elif a==1 and b==0:r1,r2=5,0
        else:r1,r2=1,1
        score1+=r1;score2+=r2
        states.append(copy.deepcopy(dict(round=t,histories=[state1,state2],scores=[score1,score2],actions=actions)))
    return states
