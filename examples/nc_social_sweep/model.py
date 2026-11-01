"""Explicit-agent, irreversible random-field activation through ORDO.

Mechanism: mean-field RFIM used as a social contagion/pressure model in NC2022.
All eligible agents in a shell act before the next shell sees their influence.
"""
import hashlib
import json
import numpy as np
from orgabm.sdk import DecisionBatch,FunctionEngine


def state_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


class SocialActivation:
    def __init__(self,*,agents=256,disorder=.8,seed=7,fields=None):
        if type(agents) is not int or not 2<=agents<=10000:raise ValueError('Use 2..10,000 agents.')
        if type(disorder) not in (int,float) or not 0<disorder<=5:raise ValueError('Use finite disorder in (0,5].')
        self.n=agents;self.disorder=disorder;self.seed=seed
        self.fields=np.random.default_rng(seed).normal(0,disorder,agents).tolist() if fields is None else list(fields)
        if len(self.fields)!=agents or not all(np.isfinite(x) for x in self.fields):raise ValueError('Invalid fixed heterogeneity.')
        self.active=[False]*agents;self.activation_time=[None]*agents
        self.outer=-1.;self.working=-1.;self.H=None;self.current_size=0;self.avalanche=0
        self.events=[];self.sizes=[];self.round=0;self.pending=None;self.phase='seed'

    def describe(self):
        return dict(scenario='social_mean_field_rfim',source_doi='10.1038/s41467-022-28964-8',
            agents=self.n,disorder=self.disorder,seed=self.seed,fields_sha256=state_hash(self.fields),
            activation='irreversible; quasi-static external field; synchronous avalanche shells',
            engine_scope='only unstable agents have an activation opportunity; seeded initiator is exogenous',
            horizon='at most 2N shells including terminal empty shells; padding carries no new decisions',
            inference='native deterministic mechanism; no LLM or human-fidelity comparison')

    def prepare(self,t):
        if self.pending is not None or t!=self.round+1:raise ValueError('Commit the pending shell first.')
        inactive=[a for a in range(self.n) if not self.active[a]]
        if self.phase=='seed' and inactive:
            ordered=sorted(inactive,key=lambda a:(self.fields[a],a));a=ordered[-1]
            first=self.fields[a];second=self.fields[ordered[-2]] if len(ordered)>1 else 0.
            gap=first-second
            self.H=-self.outer-first+(1e-6 if gap>1e-6 or gap<0 else gap/2)
            eligible=[a];self.avalanche+=1;self.current_size=0
        elif self.phase=='shell':
            eligible=[a for a in inactive if self.fields[a]+self.working+self.H>0]
        else:eligible=[]
        self.pending=dict(eligible=eligible,phase=self.phase if inactive or self.phase=='shell' else 'complete')
        questions={f't{t}_a{a}':dict(type='choice',instructions=json.dumps(dict(
            individual_field=self.fields[a],collective_field=self.outer if self.phase=='seed' else self.working,
            external_field=self.H,exogenous_seed=self.phase=='seed'),separators=(',',':')),
            criteria={'activate':'Become active.','defer':'Remain inactive.'}) for a in eligible}
        return DecisionBatch('An irreversible social activation opportunity. The native RFIM rule activates every unstable agent; the initiator is externally seeded.',questions,{q:int(q.split('_a')[1]) for q in questions})

    def advance(self,t,actions,probabilities):
        if self.pending is None:raise ValueError('Prepare first.')
        phase=self.pending['phase'];eligible=self.pending['eligible']
        if phase=='complete':
            self.round=t;self.pending=None
            return dict(round=t,complete=True,padding=True,active=self.n,state_sha256=state_hash(self.active))
        changed=[]
        for a in eligible:
            value=actions[f't{t}_a{a}']
            if value not in ('activate','defer'):raise ValueError('Illegal activation action.')
            if value=='activate':self.active[a]=True;self.activation_time[a]=t;changed.append(a)
        if phase=='seed':
            if len(changed)!=1:raise ValueError('This native-reference fixture requires its seeded initiator to activate.')
            self.working=self.outer+2./self.n;self.phase='shell'
        else:self.working+=2.*len(changed)/self.n
        self.current_size+=len(changed)
        event=dict(shell_size=len(changed),avalanche=self.avalanche,field=self.H,remaining=self.n-sum(self.active))
        self.events.append(event)
        if not eligible:
            self.sizes.append(self.current_size);self.outer+=2.*self.current_size/self.n;self.phase='seed'
        self.round=t;self.pending=None
        return dict(round=t,**event,active=sum(self.active),completed_avalanches=len(self.sizes),
            largest_completed_avalanche=max(self.sizes,default=0),
            state_sha256=state_hash(self.active),complete=all(self.active) and self.phase=='seed',padding=False)

    def snapshot(self):
        return dict(fields=self.fields,active=self.active,activation_time=self.activation_time,
            avalanche_sizes=self.sizes,events=self.events)


def native_engine():
    return FunctionEngine(lambda state,q:{'activate':1.,'defer':0.},name='published-rfim-native-activation')
