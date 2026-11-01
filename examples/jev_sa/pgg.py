"""Public-goods environment, Wang & Su (Science Advances 2026), Eq. 1/2/6.

Environment, averaged payoffs and PC opportunities are reconstructed from the
published protocol. Jev replaces the original Fermi imitation probability.
No upstream executable code is bundled or run.
"""
from collections import Counter
import json
import math
import random
from orgabm.sdk import DecisionBatch, FunctionEngine

DOI='10.1126/sciadv.aeb1263'
SOURCE_COMMIT='5a2f280bf76fe3ca36566242ca4edf5700d66229'


def make_neighbors(n,topology):
    if type(n) is not int or n<3:raise ValueError('At least three agents are required.')
    if topology=='star':return {i:([j for j in range(1,n)] if i==0 else [0]) for i in range(n)}
    if topology=='complete':return {i:[j for j in range(n) if j!=i] for i in range(n)}
    raise ValueError('Use star or complete.')


def payoffs(strategies,neighbors,synergy,cost=1.):
    """Eq. 6: average the payoff from self/neighbor-organized overlapping groups."""
    groups={i:[i,*neighbors[i]] for i in neighbors}
    benefits={i:synergy*cost*sum(strategies[j] for j in g)/len(g) for i,g in groups.items()}
    return [sum(benefits[g]-cost*strategies[i] for g in groups[i])/len(groups[i]) for i in neighbors]


class PublicGoodsPC:
    def __init__(self,*,agents=10,colonies=4,topology='star',synergy=3.,seed=7):
        self.neighbors=make_neighbors(agents,topology)
        if type(colonies) is not int or not 1<=colonies<=64 or not math.isfinite(synergy) or synergy<=1:
            raise ValueError('Use 1..64 independent groups and synergy >1.')
        self.n=agents;self.colonies=colonies;self.topology=topology;self.synergy=synergy;self.seed=seed
        self.rng=random.Random(seed);self.round=0;self.pending=None;self.events=[]
        self.strategies=[]
        for k in range(colonies):
            state=[0]*agents;state[self.rng.randrange(agents)]=1;self.strategies.append(state)
        self.initial=[list(s) for s in self.strategies]

    def describe(self):
        return dict(scenario='network_public_goods_pairwise_comparison',paper_doi=DOI,
                    agents_per_colony=self.n,independent_colonies=self.colonies,topology=self.topology,
                    synergy=self.synergy,cost=1,seed=self.seed,initial_states=self.initial,
                    source_repository='https://github.com/ChaoqianSCI/Spatial-PGGs-any-network',
                    source_commit=SOURCE_COMMIT,source_file='pgggraph_PC.py',
                    preserved='Overlapping self-and-neighbor groups; averaged payoff; random focal and neighbor; PC keep/adopt; one initial cooperator; absorbing homogeneous states.',
                    changed='External decision model replaces the original Fermi probability with selection strength .01; reduced horizon/replicates.',
                    information='Only current focal/selected-neighbor strategies and average payoffs, focal group sizes and public game rules; no other colony or future action.',
                    independent_batch='One asynchronous update in each disjoint colony per SDK round.')

    def prepare(self,t):
        if self.pending is not None or t!=self.round+1:raise ValueError('Finish the pending update first.')
        questions={};ids={};pending=[]
        for colony,state in enumerate(self.strategies):
            if len(set(state))==1:
                pending.append(dict(colony=colony,absorbed=True));continue
            focal=self.rng.randrange(self.n);neighbor=self.rng.choice(self.neighbors[focal])
            qid=f't{t}_c{colony}_a{focal}'
            item=dict(colony=colony,focal=focal,neighbor=neighbor,qid=qid,absorbed=False,query=state[focal]!=state[neighbor])
            pending.append(item)
            if not item['query']:continue
            values=payoffs(state,self.neighbors,self.synergy)
            view=dict(own_strategy='contribute' if state[focal] else 'not_contribute',
                      selected_neighbor_strategy='contribute' if state[neighbor] else 'not_contribute',
                      own_average_payoff=values[focal],selected_neighbor_average_payoff=values[neighbor],
                      contribution_cost=1,synergy_factor=self.synergy,
                      participating_group_sizes=[1+len(self.neighbors[g]) for g in [focal,*self.neighbors[focal]]])
            text=('An individual participates in overlapping public-goods groups organized by themselves and their neighbors. '
                  'A contributor pays 1 in each participating group; noncontributors pay zero. Each group multiplies total contributions by the stated synergy factor and shares it equally. '
                  'Actual payoff is the average over all groups the individual participates in. '
                  'At this update the individual can retain their current strategy or copy the strategy of the one selected neighbor. '
                  'Predict this individual\'s next choice using only the current comparison below. '
                  'The current payoffs are observations from the present strategy state. No later choices are known. '
                  +json.dumps(view,separators=(',',':')))
            questions[qid]=dict(type='choice',instructions=text,
                                criteria={'keep':'Retain the current strategy.','adopt':'Copy the selected neighbor\'s strategy.'})
            ids[qid]=colony*self.n+focal
        self.pending=pending
        return DecisionBatch('Independent local public-goods strategy comparisons in separate populations.',questions,ids)

    def advance(self,t,actions,probabilities):
        if self.pending is None or t!=self.round+1:raise ValueError('Prepare the current update first.')
        expected={p['qid'] for p in self.pending if p.get('query')}
        if set(actions)!=expected or any(v not in ('keep','adopt') for v in actions.values()):raise ValueError('Unexpected PC action set.')
        comparisons=0;adoptions=0
        for p in self.pending:
            if not p.get('query'):continue
            comparisons+=1
            if actions[p['qid']]=='adopt':
                s=self.strategies[p['colony']];s[p['focal']]=s[p['neighbor']];adoptions+=1
        self.round=t;self.pending=None
        fractions=[sum(s)/self.n for s in self.strategies]
        row=dict(update=t,monte_carlo_time=t/self.n,cooperation_fraction=sum(fractions)/self.colonies,
                 colony_cooperation=fractions,fully_cooperative=sum(x==1 for x in fractions),
                 fully_defective=sum(x==0 for x in fractions),active_colonies=sum(0<x<1 for x in fractions),
                 compared_distinct_strategies=comparisons,adopted=adoptions,
                 private_strategy_states=[list(s) for s in self.strategies])
        self.events.append(row);return row


def fermi_engine(selection=.01):
    """Unpaid comparator; no rule answers enter the external engine's questions."""
    def choose(state,q):
        payload=json.loads(q['instructions'][q['instructions'].index('{'):])
        difference=payload['selected_neighbor_average_payoff']-payload['own_average_payoff']
        p=1/(1+math.exp(-selection*difference))
        return {'keep':1-p,'adopt':p}
    return FunctionEngine(choose,name='published-PC-Fermi-comparator')
