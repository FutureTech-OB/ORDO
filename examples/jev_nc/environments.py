"""ABM worlds without an author-policy decision fallback.

Author code supplies game payoffs, population accounting, or physical movement;
the public SDK engine supplies every recorded behavioral choice.
"""
import json
import math
import random
from pathlib import Path
import numpy as np
from orgabm.sdk import DecisionBatch
from examples.nc_evolutionary_games.model import rewards
from examples.nc_additional_games.model import author_namespace, initialize, state_hash
from examples.nc_social_sweep.foraging import ForagingEnvironment, plain
from examples.nc_social_sweep.foraging_sources import load_sources, load_author


def text(value):return json.dumps(value,separators=(',',':'),allow_nan=False)


class FreshRepeatedGame:
    def __init__(self,initial='CD',pairs=4,rounds=12,seed=7):
        if initial not in ('CC','CD','DD'):raise ValueError('Unknown incident.')
        self.initial=initial;self.pairs=pairs;self.rounds=rounds;self.seed=seed;self.round=0
        self.histories=[[[initial[1],initial[0]]],[[initial[0],initial[1]]]]
        self.history=[json.loads(json.dumps(self.histories[i%2])) for i in range(2*pairs)]
        self.scores=[0]*(2*pairs)
    def describe(self):
        return dict(model='fresh_jev_repeated_game',doi='10.1038/s41467-025-67178-6',
            initial_observed_incident=self.initial,pairs=self.pairs,rounds=self.rounds,
            reused='Author simultaneous PD payoffs and private bilateral histories.',
            replaced='Both players choose fresh C/D; no trained Q table, strategy label, first-action constraint, or author answer.',
            scope='Paper-derived decision-model substitution; not MARL retraining or full evolutionary-competition replication.')
    def prepare(self,t):
        if t!=self.round+1:raise ValueError('Round order changed.')
        questions={};identities={}
        for i in range(self.pairs*2):
            q=f'pd_t{t}_a{i}';identities[q]=i
            questions[q]=dict(type='choice',instructions=text(dict(
                person=i,partner=i^1,prior_interactions=[dict(partner=p,own=o) for p,o in self.history[i]],
                own_earned_points=self.scores[i],decision='Choose your action now; the partner chooses simultaneously.')),
                criteria={'C':'Cooperate','D':'Defect'})
        return DecisionBatch('You are a person repeatedly interacting with the same partner. Points matter to you. '
            'Both cooperate: each earns 3. You cooperate and partner defects: you earn 0, partner 5. '
            'You defect and partner cooperates: you earn 5, partner 0. Both defect: each earns 1. '
            'You see only your bilateral past. The first recorded interaction has already happened; decide the next action. '
            'The interaction may continue; its ending time is not disclosed to either person.',questions,identities)
    def advance(self,t,actions,probabilities):
        chosen=[actions[f'pd_t{t}_a{i}'] for i in range(self.pairs*2)]
        mutual=0
        for i in range(0,len(chosen),2):
            a,b=chosen[i:i+2]
            if a not in ('C','D') or b not in ('C','D'):raise ValueError('Illegal PD action.')
            pa,pb=rewards(int(a=='D'),int(b=='D'));self.scores[i]+=pa;self.scores[i+1]+=pb
            self.history[i].append([b,a]);self.history[i+1].append([a,b]);mutual+=int(a==b=='C')
        self.round=t
        return dict(round=t,cooperation=chosen.count('C')/len(chosen),mutual_cooperation=mutual/self.pairs,
            mean_cumulative_payoff=sum(self.scores)/len(self.scores),actions=chosen,
            mean_cooperate_probability=sum(p['C'] for p in probabilities.values())/len(probabilities))


DONOR=[
    'Always cooperate as donor.',
    'Without information cooperate; when the recipient reward policy is known, cooperate only with reward-cooperation-only recipients.',
    'Without information defect; when the recipient reward policy is known, cooperate only with reward-cooperation-only recipients.',
    'Always defect as donor.']
REWARD=['Never reward.','Reward a donor only after cooperation.','Reward a donor only after defection.','Reward a donor after either action.']
def policy_description(code):return dict(donor=DONOR[code//4],recipient=REWARD[code%4])


class FreshSocialRewarding:
    """Synchronous policy revision with original well-mixed expected payoffs.

No call to original `step`, `fermi`, or NativeEngine. A uniform proposal only
specifies the offered alternative; the engine decides whether to adopt it.
"""
    def __init__(self,information=.5,agents=16,rounds=6,seed=7,mutation=.1):
        if agents%4 or agents<4:raise ValueError('Balanced initialization needs 4k members.')
        self.config=dict(agents=agents,rounds=rounds,information=information,mutation=mutation,
            selection=1,benefit=4,cost=1,reward=3,reward_cost=1,seed=seed)
        self.ns=author_namespace(self.config);self.donor,self.recipient=initialize(self.ns,agents)
        self.rng=random.Random(seed+921);self.round=0;self.pending=None
    def describe(self):
        return dict(model='fresh_jev_social_rewarding',doi='10.1038/s41467-022-33551-y',**self.config,
            reused='Original 16 donor/reward policies, balanced random initial traits, analytical well-mixed payoff and cooperation functions.',
            replaced='Fresh keep/adopt decisions replace Fermi imitation; uniform novel proposals still require a decision.',
            timing='All members observe start-of-sweep payoffs and revise synchronously; author code used single asynchronous updates.',
            scope='Paper-derived behavioral mechanism test, not original stationary evolutionary distribution.')
    def prepare(self,t):
        if t!=self.round+1 or self.pending is not None:raise ValueError('Commit previous sweep.')
        ns=self.ns;n=self.config['agents'];dd=ns['get_donor_dist'](self.donor);rd=ns['get_recep_dist'](self.recipient)
        codes={i:4*self.donor[i]+self.recipient[i] for i in self.donor}
        def payoff(code,focal_code):
            # A counterfactual offered policy plays the *other n-1 members*.
            # Subtract the actual focal traits, not the offered policy itself.
            d,r=code//4,code%4;fd,fr=focal_code//4,focal_code%4
            total=sum(ns['payoff_A'][d,j]*rd[j]+ns['payoff_B'][j,r]*dd[j] for j in range(4))
            return float(.5*(total-ns['payoff_A'][d,fr]-ns['payoff_B'][fd,r])/(n-1))
        questions={};identities={};self.pending={}
        for i in range(1,n+1):
            novel=self.rng.random()<self.config['mutation']
            if novel:candidate=self.rng.choice([x for x in range(16) if x!=codes[i]])
            else:candidate=codes[self.rng.choice([j for j in range(1,n+1) if j!=i])]
            q=f'reward_t{t}_a{i}';identities[q]=i;self.pending[q]=(i,candidate)
            questions[q]=dict(type='choice',instructions=text(dict(person=i,
                own_policy=policy_description(codes[i]),own_expected_points=payoff(codes[i],codes[i]),
                offered_policy=policy_description(candidate),offered_expected_points=payoff(candidate,codes[i]),
                offered_source='a newly considered policy' if novel else 'another population member',
                previous_population_cooperation=float(ns['get_coop_rate'](ns['get_stg_dist'](self.donor,self.recipient))),
                information_probability=self.config['information'])),
                criteria={'keep':'Keep my current policy.','adopt':'Adopt the offered policy for subsequent interactions.'})
        return DecisionBatch('You are a member of a repeatedly interacting population. Random pairs alternate donor and recipient roles. '
            'A cooperating donor pays 1 point and gives the recipient 4; defection transfers nothing. '
            'A recipient may pay 1 to give the donor 3 reward points. Information probability is the chance a donor learns a recipient reward policy before acting. '
            'You may revise your donor and recipient policies together. Expected points are analytical averages against the current population, excluding yourself. '
            'Choose whether to retain your policy or use the offered one; consider your earnings and your interactions with others.',questions,identities)
    def advance(self,t,actions,probabilities):
        adopted=0
        for q,(i,candidate) in self.pending.items():
            if actions[q]=='adopt':self.donor[i]=candidate//4;self.recipient[i]=candidate%4;adopted+=1
            elif actions[q]!='keep':raise ValueError('Invalid policy decision.')
        counts=self.ns['get_stg_dist'](self.donor,self.recipient);n=self.config['agents'];self.pending=None;self.round=t
        return dict(round=t,cooperation=float(self.ns['get_coop_rate'](counts)),
            social_rewarding_share=sum(counts[i] for i in (1,5,9,13))/n,
            antisocial_rewarding_share=sum(counts[i] for i in (2,6,10,14))/n,
            adopted_share=adopted/n,strategy_counts=counts,state_sha256=state_hash(self.donor,self.recipient))


class FreshForaging(ForagingEnvironment):
    def __init__(self,task,sim,cache,*,environment='smooth',social_cues=True,seed=7,steps=120):
        super().__init__(task,sim,cache,environment=environment,policy='asocial',seed=seed,agents=4,steps=steps,mining_steps=9)
        self.social_cues=social_cues
    def describe(self):
        d=super().describe();d.pop('native_sampling',None);d.pop('policy',None)
        d.update(model='fresh_jev_collective_foraging',social_cues=self.social_cues,
            decision='Every next-cell choice comes from the external engine; native Policy.sample_next_cell is never called.',
            candidate_set='Up to 24 unrevealed cells: 12 nearest to self and 12 evenly spaced over remaining row-major coordinates. No hidden reward is used.',
            ablation='Explicit other-agent positions/directions/success flags withheld when social_cues=False. Visible reward observations and depletion mask remain.',
            scope='Two fixed author maps, reduced horizon and shortlist; not original fitted policy or full empirical reproduction.')
        return d
    def prepare(self,t):
        if self.pending is not None or t!=self.round+1:raise ValueError('Commit previous goal.')
        if self.final_result is not None:self.pending={};return DecisionBatch('Completed foraging world.',{}, {})
        step,a,view,state,policy,rng=self.current
        own=state.agent_locs[:,a];eligible=np.argwhere(~state.revealed_map)
        distance=np.abs(eligible-own).sum(axis=1)
        nearest=np.argsort(distance,kind='stable')[:12].tolist()
        remainder=[i for i in range(len(eligible)) if i not in nearest]
        spread=[] if not remainder else [remainder[i] for i in np.linspace(0,len(remainder)-1,min(12,len(remainder)),dtype=int)]
        cells=eligible[nearest+spread]
        choices={f'cell_{int(x)}_{int(y)}':f'Forage at ({int(x)},{int(y)}), travel distance {int(abs(x-own[0])+abs(y-own[1]))}.' for x,y in cells}
        observed=[dict(x=int(x),y=int(y),reward=int(view.agent_rewards_map[x,y])) for x,y in np.argwhere(~np.isnan(view.agent_rewards_map))]
        record=dict(person=a,physical_step=step,own_position=plain(own),own_direction=plain(state.agent_dirs[:,a]),
            observed_rewards=observed,resource_pattern=self.config['environment'],
            choice='Choose the next block to forage. Rewards of unmined blocks are unknown.')
        if self.social_cues:
            record['other_people']=[dict(person=i,position=plain(view.agent_locs[:,i]),direction=plain(view.agent_dirs[:,i]),
                recently_seen_rewarded=bool(view.rewarded_agents[i])) for i in range(4) if i!=a and not np.isnan(view.agent_locs[:,i]).any()]
        q=f'forage_t{t}_a{a}';self.pending={q:choices}
        return DecisionBatch('You are one of four people searching the same finite resource field. Each collected reward adds one point to your own earnings. '
            'Moving takes one physical step per grid edge. Mining a block takes nine additional countdown steps plus action transitions. '
            'Each block can be collected only once; others compete for the same blocks. '
            'In smooth fields rewards are clustered; in random fields they are spatially independent. '
            'Use your observed outcomes and any available local observations. No unobserved reward locations are supplied.',
            {q:dict(type='choice',instructions=text(record),criteria=choices)},{q:a})


def foraging_modules(cache='.buildtmp/nc-foraging-source'):
    load_sources(cache,download=False)
    with np.errstate(divide='ignore',invalid='ignore'):task,sim,transform=load_author(cache)
    return task,sim,cache
