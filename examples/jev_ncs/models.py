"""Environments retain feedback; an external engine chooses substantive actions.

Native probabilities are private baseline data, never part of Jev questions.
These are declared decision-level transfers, not bitwise author simulations.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import random
import zipfile

import networkx as nx
from orgabm.sdk import DecisionBatch
from examples.ncs_colocation.sources import checkout,dataset


class Protocol:
    def start(self,t):
        if self.pending is not None or t!=self.round+1:raise ValueError('Finish the prior transition first.')
        self.pending={};self.rules={}

    def check(self,t,actions):
        if self.pending is None or t!=self.round+1 or set(actions)!=set(self.pending):raise ValueError('Invalid action batch.')
        if any(a not in self.pending[q]['choices'] for q,a in actions.items()):raise ValueError('Unavailable action.')

    def finish(self,t,row):
        self.round=t;self.pending=None;self.records.append(row);return row


class RuleEngine:
    def __init__(self,env):self.env=env
    def decide(self,state,questions):
        if set(questions)!=set(self.env.rules):raise ValueError('Rule probabilities not prepared.')
        return deepcopy(self.env.rules)
    def usage(self):return dict(engine='paired-original-weight-rule-on-transferred-environment',recorded_input_cost_usd=0)


def normalize(weights):
    total=sum(weights.values())
    if not math.isfinite(total) or total<=0:raise ValueError('Invalid baseline mass.')
    return {k:v/total for k,v in weights.items()}


class CollectiveMobility(Protocol):
    """Small torus, sampled choice sets, frozen density and individual visits."""
    def __init__(self,seed=7,memory_visible=True,population=16,side=12):
        self.seed=seed;self.rng=random.Random(seed);self.memory_visible=memory_visible;self.n=population;self.side=side
        self.positions=[(side//2,side//2) for _ in range(population)]
        self.visits=[Counter({p:1}) for p in self.positions];self.round=0;self.pending=None;self.records=[]
        file=Path('.buildtmp/ncs-mobility-native/main.cpp');raw=file.read_bytes()
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!='306e9b8dd06640920f098e3a72ef8456ab144c2b':raise ValueError('CMM source differs.')
        self.source_sha256=hashlib.sha256(raw).hexdigest()

    def describe(self):
        return dict(paper_id='ncs_cmm_2021',doi='10.1038/s43588-021-00160-6',population=self.n,side=self.side,
            seed=self.seed,memory_visible=self.memory_visible,source_sha256=self.source_sha256,
            scope='Jev destination-choice transfer, not original 300x300 lattice or published urban-scaling validation.',
            retained=['Frozen prior-period population','Distance and occupancy feedback','Individual visit frequencies','Synchronous movement'],
            changed=['12x12 torus;16 residents','Six sampled destinations per person','Jev replaces exploration/return and gravity choices',
                     'No-memory condition hides personal history and uses exploration-only paired rule'],
            benchmark='Paired rule uses original rho0=1e-12, alpha=-2.55, gamma=.21 normalized on each sampled menu.')

    def distance(self,a,b):return math.hypot(*[min(abs(x-y),self.side-abs(x-y)) for x,y in zip(a,b)])

    def prepare(self,t):
        self.start(t);population=Counter(self.positions);questions={};ids={}
        sites=[(x,y) for x in range(self.side) for y in range(self.side)]
        for i,pos in enumerate(self.positions):
            # Balanced proposal exposes both revisits and unexplored destinations;
            # proposal scheme is a declared reduced choice-set adaptation.
            familiar=[p for p in self.visits[i] if p!=pos]
            chosen=self.rng.sample(familiar,min(2,len(familiar)))
            occupied=[p for p in population if p!=pos and p not in chosen]
            chosen+=self.rng.sample(occupied,min(2,len(occupied)))
            unused=[p for p in sites if p!=pos and p not in chosen]
            chosen+=self.rng.sample(unused,6-len(chosen));self.rng.shuffle(chosen)
            choices={f'site-{j}':p for j,p in enumerate(chosen)};criteria={}
            for key,p in choices.items():
                features=dict(location=list(p),travel_distance=round(self.distance(pos,p),3),residents_last_period=population[p])
                if self.memory_visible:features['your_previous_visits']=self.visits[i][p]
                criteria[key]=json.dumps(features)
            q=f'move-{t}-{i}'
            questions[q]=dict(type='choice',instructions=json.dumps(dict(person=f'Resident {i}',current_location=pos,
                task='Select where this resident would next travel among the available destinations. Predict a choice; there is no desired population pattern.',
                history_available=self.memory_visible)),criteria=criteria);ids[q]=i
            self.pending[q]=dict(choices=choices,person=i)
            explore={k:(population[p]+1e-12)*self.distance(pos,p)**-2.55 for k,p in choices.items() if not self.memory_visible or not self.visits[i][p]}
            returns={k:self.visits[i][p] for k,p in choices.items() if self.visits[i][p]}
            if not explore:explore={k:self.distance(pos,p)**-2.55 for k,p in choices.items()}
            e=normalize(explore);r=normalize(returns) if returns else {}
            prob=len(self.visits[i])**-.21 if self.memory_visible and r else 1
            self.rules[q]={k:prob*e.get(k,0)+(1-prob)*r.get(k,0) for k in choices}
        return DecisionBatch('Residents move in a shared city. Report likely choices from local observations.',questions,ids)

    def advance(self,t,actions,probabilities):
        self.check(t,actions);updates=[];revisits=0
        for q,a in actions.items():
            item=self.pending[q];i=item['person'];p=item['choices'][a];revisits+=bool(self.visits[i][p]);updates.append((i,p))
        for i,p in updates:self.positions[i]=p;self.visits[i][p]+=1
        counts=Counter(self.positions)
        if sum(counts.values())!=self.n:raise AssertionError('Population mass changed.')
        return self.finish(t,dict(round=t,population=self.n,occupied_sites=len(counts),concentration=sum((v/self.n)**2 for v in counts.values()),
            revisit_rate=revisits/self.n,mean_unique_locations=sum(map(len,self.visits))/self.n,
            cumulative_person_moves=t*self.n))


class Colocation(Protocol):
    """Public candidate ties, researcher contact choice, lagged graph feedback."""
    def __init__(self,seed=7,policy='remote_return',population=200,active=16,lengths=(4,4,4)):
        if policy not in ('continuous','remote_return'):raise ValueError('Unknown policy.')
        self.seed=seed;self.rng=random.Random(seed);self.policy=policy;self.active=active;self.lengths=lengths
        root=checkout();self.nodes,self.distances,self.dates,self.memory=dataset(root,population)
        self.memory=deepcopy(self.memory);self.round=0;self.pending=None;self.records=[]
        self.previous=nx.Graph();self.previous.add_nodes_from(self.nodes)
        self.candidates={i:[] for i in self.nodes}
        for edge in self.memory:
            a,b=edge;self.candidates[a].append(b);self.candidates[b].append(a)
        self.actors=[i for i in self.nodes if self.candidates[i]]
        if len(self.actors)<self.active:raise ValueError('Too few nonisolated public-demo actors.')

    def describe(self):
        return dict(paper_id='ncs_colocation_2022',doi='10.1038/s43588-022-00296-z',seed=self.seed,policy=self.policy,
            population=len(self.nodes),active_each_day=self.active,phase_days=self.lengths,
            scope='Decision-level communication transfer on author public data, not original two-stage edge protocol or MIT empirical estimate.',
            retained=['Author eligible tie pool and public distances/department-pair indicators','Five-day periodicity','Past contact history',
                      'Lagged shared-contact closure','Remote phase sets distances to2000;return restores source distances'],
            changed=['16 rotating researchers choose at most one contact/day','Up to six candidate contacts and no-contact',
                     'Jev replaces global 50+20 edge samples without replacement','Closure from prior day rather than within-day first-stage graph'],
            benchmark='Original feature weights applied to the same reduced choices; no-contact baseline weight=2000 is new and declared.')

    def prepare(self,t):
        self.start(t);questions={};ids={};day=9+t
        remote=self.policy=='remote_return' and self.lengths[0]<t<=sum(self.lengths[:2])
        active=[self.actors[(self.active*(t-1)+j)%len(self.actors)] for j in range(self.active)]
        for actor in active:
            candidates=sorted(self.candidates[actor]);chosen=self.rng.sample(candidates,min(6,len(candidates)))
            self.rng.shuffle(chosen);choices={f'contact-{j}':other for j,other in enumerate(chosen)};choices['none']=None
            criteria={'none':'Do not initiate a contact today.'};weights={'none':2000.0}
            for key,other in choices.items():
                if other is None:continue
                edge=tuple(sorted((actor,other)));distance,same=self.distances[edge]
                distance=2000.0 if remote else float(distance);distance=1500.0 if not math.isfinite(distance) else distance
                history=self.memory[edge];frequency=sum(math.exp(-(day-x)/562) for x in history if x<day)
                periodic=(day-5) in history
                common=len(set(self.previous[actor])&set(self.previous[other]));near=distance<=150
                features=dict(researcher=str(other),office_distance_m=round(distance,2),same_department=bool(same),
                    previous_contacts=len(history),last_contact_days_ago=day-max(history) if history else None,
                    contacted_five_workdays_ago=periodic,shared_contacts_previous_day=common)
                criteria[key]=json.dumps(features)
                # Published weights, evaluated on declared per-person menu.
                weights[key]=((1/1.5 if near else 1.5)*80000*periodic
                    +(1/1.1 if near else 1.1)*90000*bool(same)+frequency
                    +(2 if near else .5)*2000*(frequency==0)
                    +(1/1.5 if near else 1.5)*200000*(common>0))
            q=f'contact-{t}-{actor}';questions[q]=dict(type='choice',instructions=json.dumps(dict(researcher=str(actor),workday=t,
                arrangement='working remotely' if remote else 'working on campus',
                task='Predict whom this researcher would initiate a work communication with today, or no contact. Contacts can be online or in person.')),
                criteria=criteria);ids[q]=str(actor);self.pending[q]=dict(choices=choices,actor=actor)
            self.rules[q]=normalize(weights)
        return DecisionBatch('Researchers choose contacts in an evolving organizational network.',questions,ids)

    def advance(self,t,actions,probabilities):
        self.check(t,actions);edges=set();new=0;cross=0;day=9+t
        for q,a in actions.items():
            item=self.pending[q];other=item['choices'][a]
            if other is not None:edges.add(tuple(sorted((item['actor'],other))))
        for edge in sorted(edges):
            new+=not bool(self.memory[edge]);cross+=not bool(self.distances[edge][1]);self.memory[edge].append(day)
        graph=nx.Graph();graph.add_nodes_from(self.nodes);graph.add_edges_from(edges);self.previous=graph
        return self.finish(t,dict(round=t,population=len(self.nodes),contact_edges=len(edges),new_ties=new,cross_department_ties=cross,
            local_bridges=len(list(nx.local_bridges(graph,with_span=False))),components=nx.number_connected_components(graph),
            remote=self.policy=='remote_return' and self.lengths[0]<t<=sum(self.lengths[:2]),phase=0 if t<=self.lengths[0] else 1 if t<=sum(self.lengths[:2]) else 2))


class DynamicGame(Protocol):
    """Author death-birth/mutation/network sequence; replace only parent choice."""
    def __init__(self,seed=7,condition='switching',population=6,mutation=.01,delta=.1):
        if condition not in ('ring','star','switching'):raise ValueError('Unknown topology.')
        self.seed=seed;self.rng=random.Random(seed);self.n=population;self.condition=condition;self.mutation=mutation;self.delta=delta
        self.state=[self.rng.randrange(2) for _ in range(population)];self.network=1 if condition=='star' else 0
        self.graphs=[nx.cycle_graph(population),nx.star_graph(population-1)]
        self.round=0;self.pending=None;self.records=[];self.sum_cooperation=0.0;self.transitions=0
        raw=Path('.buildtmp/ncs-dynamic-games/author-release.zip').read_bytes()
        if hashlib.md5(raw).hexdigest()!='15d12d6f02aea003e4d37985059a9a31':raise ValueError('Dynamic-game release differs.')
        self.archive_sha256=hashlib.sha256(raw).hexdigest()

    def describe(self):
        return dict(paper_id='ncs_dynamic_2026',doi='10.1038/s43588-026-01068-9',code_doi='10.5281/zenodo.22152088',
            archive_sha256=self.archive_sha256,seed=self.seed,condition=self.condition,population=self.n,mutation=self.mutation,selection_intensity=self.delta,
            scope='Decision-level parent-selection transfer, not the structure-coefficient theorem or published stationary simulation.',
            retained=['One uniformly random death per iteration','Parent must be a current neighbor','Offspring copies parent strategy',
                'Mutation uniformly redraws a strategy','Exogenous network transition after replacement','Accumulated donation payoff b4,c1;recomputed after transitions'],
            changed=['Jev replaces fitness-weighted parent draw','Reduced100iterations','delta=.1 strong-selection setting rather than demo.002',
                'Python random stream, not Julia bitwise execution','Short-run mean includes initialization;not stationary estimate'],
            benchmark='Same protocol with parent weights exp(delta*payoff);ring/star fixed or switching q=1/(10*N).')

    def payoffs(self):
        # Strategy 0=cooperate,1=defect; author A=[[b-c,-c],[b,0]].
        A=((3,-1),(4,0));g=self.graphs[self.network]
        return [sum(A[self.state[i]][self.state[j]] for j in g[i]) for i in range(self.n)]

    def prepare(self,t):
        self.start(t);death=self.rng.randrange(self.n);payoff=self.payoffs();neighbors=list(self.graphs[self.network][death]);self.rng.shuffle(neighbors)
        choices={f'neighbor-{j}':person for j,person in enumerate(neighbors)}
        q=f'parent-{t}';criteria={k:json.dumps(dict(person=p,strategy='cooperate' if self.state[p]==0 else 'defect',accumulated_payoff=payoff[p])) for k,p in choices.items()}
        self.automatic_parent=None
        if len(choices)==1:
            # A star leaf has only the hub as a valid source: no decision-model
            # call is needed or counted for this deterministic protocol event.
            self.automatic_parent=(death,next(iter(choices.values())))
            return DecisionBatch('A degree-one focal position has exactly one eligible strategy source.',{}, {})
        self.pending[q]=dict(choices=choices,death=death)
        self.rules[q]=normalize({k:math.exp(self.delta*payoff[p]) for k,p in choices.items()})
        prompt=dict(focal_person=death,network='ring' if self.network==0 else 'star',own_strategy='cooperate' if self.state[death]==0 else 'defect',
            own_payoff=payoff[death],donation_game='Each cooperating neighbor gives benefit4; each act of cooperation costs1 to its actor.',
            process='The focal position is being replaced. Choose which current neighbor is likely to supply the copied strategy. One neighbor must be chosen; subsequent mutation and network changes are handled by the environment.',
            task='Predict the strategy-source choice from the observed local alternatives. No strategy is prescribed.')
        return DecisionBatch('Donation-game strategies evolve through one local replacement event.',
            {q:dict(type='choice',instructions=json.dumps(prompt),criteria=criteria)},{q:death})

    def advance(self,t,actions,probabilities):
        self.check(t,actions)
        automatic=self.automatic_parent is not None
        if automatic:death,parent=self.automatic_parent;item=dict(death=death)
        else:q=next(iter(self.pending));item=self.pending[q];parent=item['choices'][actions[q]]
        self.state[item['death']]=self.state[parent]
        mutated=self.rng.random()<self.mutation
        if mutated:self.state[item['death']]=self.rng.randrange(2)
        changed=False
        transition_draw=self.rng.random()
        if self.condition=='switching' and transition_draw<1/(10*self.n):self.network=1-self.network;self.transitions+=1;changed=True
        cooperation=self.state.count(0)/self.n;self.sum_cooperation+=cooperation
        return self.finish(t,dict(round=t,cooperation=cooperation,mean_cooperation=self.sum_cooperation/t,network=self.network,
            network_transitions=self.transitions,parent=parent,focal=item['death'],mutated=mutated,network_changed=changed,
            payoff_mean=sum(self.payoffs())/self.n,population=self.n,automatic_single_neighbor=automatic))
