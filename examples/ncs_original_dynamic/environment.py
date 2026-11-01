"""Full-neighbor environment for a future Jev replacement experiment.

This is an explicit Python reconstruction of the author Julia event semantics;
the native baseline uses the actual pinned Julia kernel instead. No API calls.
"""
import hashlib
import json
import math
import random
import numpy as np
from orgabm.sdk import DecisionBatch


def core_periphery(nc=8,np_=100):
    if type(nc) is not int or nc<4 or nc%2 or type(np_) is not int or np_<1:raise ValueError('Even ring core and nonempty periphery required.')
    n=nc+np_;w=np.zeros((2,n,n),dtype=float)
    for layer in range(2):
        for i in range(nc):w[layer,i,(i+1)%nc]=w[layer,(i+1)%nc,i]=1
        hubs=range(nc//2) if layer==0 else range(nc//2,nc)
        for i in hubs:w[layer,i,nc:]=w[layer,nc:,i]=1
    return w


class DynamicNetwork:
    """One synchronous SDK round = one original sequential replacement event."""
    def __init__(self,*,nc=8,periphery=100,mutation=.05,tau=1.,selection=.01,
                 network='dynamic',iterations=100_000_000,seed=2026103000):
        if network not in ('dynamic','static') or not 0<=mutation<=1 or iterations<1:raise ValueError('Invalid original configuration.')
        self.nc=nc;self.np=periphery;self.n=nc+periphery;self.u=mutation;self.tau=tau;self.delta=selection
        self.w=core_periphery(nc,periphery);p=1/(tau*self.n)
        if p>1:raise ValueError('Invalid transition probability.')
        self.q=np.array([[1-p,p],[p,1-p]]) if network=='dynamic' else np.eye(2)
        self.mode=network;self.iterations=iterations;self.seed=seed;self.rng=random.Random(seed)
        self.A=np.array([[1.,-1.],[2.,0.]]) # b=2,c=1
        self.state=np.array([self.rng.randrange(2) for _ in range(self.n)],dtype=int)
        self.layer=0;self.round=0;self.pending=None;self.switches=0;self.sampled=0;self.cooperation_sum=0.
        self.refresh()
    def refresh(self):
        self.reward=(self.w[self.layer]*self.A[self.state[:,None],self.state[None,:]]).sum(axis=1)
        self.fecundity=np.exp(self.delta*self.reward)
    def describe(self):
        return dict(doi='10.1038/s43588-026-01068-9',model='full_original_parameter_dynamic_network_reconstruction',
            published_figure='Extended Data Fig.2 donation',core=self.nc,periphery=self.np,population=self.n,
            mutation=self.u,rescaled_duration=self.tau,selection=self.delta,network=self.mode,
            iterations=self.iterations,burnin_iterations=int(.05*self.iterations),benefit=2,cost=1,
            candidate_menu='Every positive-weight neighbor of the focal node; no truncation.',
            event_order='uniform focal -> external neighbor selection -> copy -> host mutation -> host Markov switch -> reward update -> post-burnin count',
            engine_boundary='The external model replaces the native w*exp(delta*reward) neighbor-selection distribution; delta is retained in state/metadata but its original effect cannot be asserted after replacement.',
            scope='Python event reconstruction; no claimed exact Julia RNG path or native-source execution in this adapter. Full native baseline is separately executed in Julia.')
    def prepare(self,t):
        if t!=self.round+1 or self.pending is not None:raise ValueError('Commit the prior replacement event first.')
        death=self.rng.randrange(self.n);neighbors=np.flatnonzero(self.w[self.layer,death]>0).tolist()
        self.pending=dict(focal=death,neighbors=neighbors)
        criteria={f'neighbor_{i}':f'Copy member {i}, whose current strategy is '+('cooperate' if self.state[i]==0 else 'defect')+'.' for i in neighbors}
        record=dict(focal_member=death,own_strategy='cooperate' if self.state[death]==0 else 'defect',
            own_accumulated_payoff=float(self.reward[death]),network_layer=self.layer+1,
            neighbors=[dict(member=i,strategy='cooperate' if self.state[i]==0 else 'defect',
                accumulated_payoff=float(self.reward[i]),degree=int(self.w[self.layer,i].sum()),
                link_weight=float(self.w[self.layer,death,i])) for i in neighbors])
        q=f'event{t}_a{death}'
        return DecisionBatch('A member in a changing interaction network is selected to revise its behavioral strategy by copying one of its current neighbors. '
            'Neighbors interact using the donation game: each cooperator pays1 per interaction and gives the other member2; defectors give nothing. '
            'The stated payoff is accumulated across all current neighbors. Select one offered neighbor to copy; do not invent a neighbor or action. '
            'The environment subsequently applies its original random mutation and network-switch mechanisms.',
            {q:dict(type='choice',instructions=json.dumps(record,separators=(',',':')),criteria=criteria)},{q:death})
    def advance(self,t,actions,probabilities):
        if self.pending is None:raise ValueError('Prepare the event first.')
        death=self.pending['focal'];qid=f'event{t}_a{death}';action=actions[qid]
        birth=int(action.removeprefix('neighbor_'))
        if birth not in self.pending['neighbors']:raise ValueError('Neighbor outside the original complete candidate set.')
        self.state[death]=self.state[birth]
        mutated=self.rng.random()<self.u
        if mutated:self.state[death]=self.rng.randrange(2)
        draw=self.rng.random();new_layer=0 if draw<self.q[self.layer,0] else 1
        self.switches+=int(new_layer!=self.layer);self.layer=new_layer;self.refresh()
        self.round=t;self.pending=None;cooperation=float((self.state==0).mean())
        if t>.05*self.iterations:self.sampled+=1;self.cooperation_sum+=cooperation
        return dict(event=t,focal=death,copied_neighbor=birth,mutated=mutated,network_layer=self.layer+1,
            network_switches=self.switches,cooperation=cooperation,post_burnin_samples=self.sampled,
            post_burnin_mean_cooperation=self.cooperation_sum/self.sampled if self.sampled else None,
            state_sha256=hashlib.sha256(self.state.tobytes()+bytes([self.layer])).hexdigest())


class NativeRule:
    """No API: reconstructed original distribution, useful for interface checks."""
    def __init__(self,world):self.world=world
    def decide(self,state,questions):
        w=self.world;focal=w.pending['focal'];neighbors=w.pending['neighbors']
        weights=[w.w[w.layer,focal,i]*w.fecundity[i] for i in neighbors];mass=sum(weights)
        return {qid:{f'neighbor_{i}':weight/mass for i,weight in zip(neighbors,weights)} for qid in questions}
    def usage(self):return dict(engine='reconstructed-native-selection',actual_model_api_calls=0,cost_usd=0)
