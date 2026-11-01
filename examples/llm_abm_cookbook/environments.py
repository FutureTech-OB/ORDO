"""Two published LLM interaction protocols behind ORDO's Environment contract.

No downloaded code executes. Historical naming-game choices are replayable;
opinion macro traces remain macro evidence and are not converted into fake logs.
"""
from collections import Counter
import copy
import hashlib
import json
import random
import string
from orgabm.sdk import DecisionBatch


HISTORY_FIELDS=('my_history','partner_history','interactions','score_history','outcome')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def recover_initial_agents(source_run):
    counts=Counter(a for pair in source_run['tracker']['players'] for a in pair)
    initial={}
    for a,final in source_run['simulation'].items():
        row=copy.deepcopy(final)
        # Minority records prefill five fictitious Q/Q outcomes and scores,
        # but do not prefill partner identity lists. Recover each prefix separately.
        for key in HISTORY_FIELDS:
            start=len(row[key])-counts[a]
            if start<0: raise ValueError('Archive history is shorter than recorded events.')
            row[key]=row[key][:start]
        if len({len(row[k]) for k in HISTORY_FIELDS if k!='interactions'})!=1:
            raise ValueError('Prefilled action/payoff histories differ in length.')
        row['score']=row['score_history'][-1] if row['score_history'] else 0
        if row['score']!=sum(row['outcome']): raise ValueError('Initial source score is inconsistent.')
        initial[a]=row
    return initial


class NamingGame:
    def __init__(self,*,agents=24,options=('Q','M'),memory_size=5,seed=7,
                 reward=100,penalty=-50,source_run=None):
        if type(agents) is not int or agents<2 or len(set(options))!=len(options) or not options:
            raise ValueError('Use distinct names and at least two agents.')
        if type(memory_size) is not int or memory_size<1: raise ValueError('Use a positive memory length.')
        self.options=list(options); self.memory_size=memory_size
        self.seed,self.reward,self.penalty=seed,reward,penalty
        self.rng=random.Random(seed); self.option_rng=random.Random(seed+100000)
        self.source_run=copy.deepcopy(source_run)
        self.agents=recover_initial_agents(source_run) if source_run else {
            a:dict(my_history=[],partner_history=[],interactions=[],score_history=[],outcome=[],score=0,
                   committed_tag=False,neighbours=[b for b in range(1,agents+1) if b!=a]) for a in range(1,agents+1)}
        self.n=len(self.agents); self.initial_sha256=digest(self.agents)
        self.committed_to=source_run.get('convergence',{}).get('committed_to') if source_run else None
        self.events=[]; self.round=0; self.prepared=None; self.views={}
        if source_run:
            lengths={len(v) for v in source_run['tracker'].values()}
            if len(lengths)!=1: raise ValueError('Archive tracker lengths differ.')

    def describe(self):
        return dict(scenario='llm_naming_game',paper_doi='10.1126/sciadv.adu9368',agents=self.n,
                    memory_size=self.memory_size,options=self.options,reward=self.reward,penalty=self.penalty,
                    seed=self.seed,initial_state_sha256=self.initial_sha256,
                    mode='archived_sampled_actions' if self.source_run else 'fresh_engine',
                    option_order='fresh seeded order; original order was not recorded in archive')

    def local_view(self,a):
        row=self.agents[a]; h=self.memory_size
        return dict(history=[dict(round=i+1,own=x,partner=y,payoff=p)
            for i,(x,y,p) in enumerate(zip(row['my_history'][-h:],row['partner_history'][-h:],row['outcome'][-h:]))],
            local_score=sum(row['outcome'][-h:]))

    def prepare(self,t):
        if self.prepared is not None or t!=self.round+1: raise ValueError('Complete the previous interaction.')
        if self.source_run:
            pair=self.source_run['tracker']['players'][t-1]
        else:
            a=self.rng.choice(list(self.agents)); pair=[a,self.rng.choice(self.agents[a]['neighbours'])]
        if len(set(pair))!=2: raise ValueError('Each pair needs two distinct agents.')
        self.prepared=(t,list(pair)); questions,ids,self.views={},{},{}
        for a in pair:
            row=self.agents[a]
            if row.get('committed_tag'):
                if self.committed_to not in self.options: raise ValueError('Missing committed action.')
                continue
            view=self.local_view(a); self.views[a]=view
            options=list(self.options); self.option_rng.shuffle(options)
            text=(f'Player 1 and Player 2 simultaneously choose one name from {options}. '
                  f'Matching names reward each player {self.reward}; different names give each player {self.penalty}. '
                  'Forecast Player 1\'s next choice to maximize their points given the other player. '
                  'Only the following recent personal history is available. '
                  f'History: {json.dumps(view["history"])}. Current score within this history: {view["local_score"]}. '
                  f'This is local round {len(view["history"])+1}.')
            qid=f't{t}_a{a}'
            questions[qid]=dict(type='choice',instructions=text,criteria={x:f'Choose name {x}.' for x in options})
            ids[qid]=a
        # No population size, global convention, partner identity/current action.
        return DecisionBatch('Predict each player independently from that player\'s permitted history.',questions,ids)

    def advance(self,t,actions,probabilities):
        if self.prepared is None or self.prepared[0]!=t: raise ValueError('Prepare the interaction first.')
        pair=self.prepared[1]; chosen=[]
        for a in pair:
            action=self.committed_to if self.agents[a].get('committed_tag') else actions[f't{t}_a{a}']
            if action not in self.options: raise ValueError('Illegal name.')
            chosen.append(action)
        outcome=self.reward if chosen[0]==chosen[1] else self.penalty
        for i,a in enumerate(pair):
            row=self.agents[a]; row['score']+=outcome
            for key,value in [('my_history',chosen[i]),('partner_history',chosen[1-i]),('interactions',pair[1-i]),
                              ('score_history',row['score']),('outcome',outcome)]: row[key].append(value)
        self.events.append(dict(players=pair,answers=chosen,outcome=int(chosen[0]==chosen[1])))
        self.round=t; self.prepared=None
        return dict(interaction=t,population_round=t/self.n,players=pair,answers=chosen,
                    successful=int(chosen[0]==chosen[1]),payoff=outcome,
                    recent_success=sum(e['outcome'] for e in self.events[-3*self.n:])/min(t,3*self.n),
                    local_view_sha256={str(a):digest(v) for a,v in self.views.items()})


class ArchivedNamingEngine:
    """Recorded LLM actions as one-hot decisions, not recorded model probabilities."""
    def __init__(self,run): self.run=run
    def decide(self,state,questions):
        result={}
        for qid,q in questions.items():
            step,agent=qid.split('_'); t=int(step[1:])-1; a=int(agent[1:])
            index=self.run['tracker']['players'][t].index(a)
            chosen=self.run['tracker']['answers'][t][index]
            result[qid]={x:float(x==chosen) for x in q['criteria']}
        return result
    def usage(self):
        return dict(engine='archived-author-LLM-actions',successful_requests=0,
                    recorded_input_cost_usd=0,probability_semantics='one_hot_recorded_sample_not_model_probabilities')


class MajorityOpinion:
    def __init__(self,agents=50,seed=7):
        if type(agents) is not int or agents<4 or agents%2: raise ValueError('Use an even population >=4.')
        self.n=agents; self.rng=random.Random(seed); self.seed=seed
        self.opinions=[1]*(agents//2)+[-1]*(agents//2)
        self.rng.shuffle(self.opinions); self.round=0; self.prepared=None

    def describe(self):
        return dict(scenario='llm_majority_opinion',paper_doi='10.1126/sciadv.aea6091',agents=self.n,seed=self.seed,
                    schedule='one random member per update; dt=1/N; no memory, reward or own opinion in input',
                    prompt_fidelity='semantic adaptation, not original token/output-format replication')

    def prepare(self,t):
        if self.prepared is not None or t!=self.round+1: raise ValueError('Complete the previous update.')
        selected=self.rng.randrange(self.n)
        labels=['k','z'] if self.rng.random()<.5 else ['z','k']; mapping={1:labels[0],-1:labels[1]}
        alias_length=2
        while 62**alias_length<self.n: alias_length+=1
        aliases=self.rng.sample(range(62**alias_length),self.n)
        chars=string.ascii_letters+string.digits
        def name(value): return ''.join(chars[(value//62**i)%62] for i in range(alias_length))
        peers=[dict(name=name(aliases[i]),opinion=mapping[x]) for i,x in enumerate(self.opinions) if i!=selected]
        self.rng.shuffle(peers)
        text='Below are all your friends and the opinions they support. Choose the opinion you want to support.\n'
        text+='\n'.join(f'{x["name"]}: {x["opinion"]}' for x in peers)
        qid=f't{t}_a{selected}'; self.prepared=(t,selected,mapping,peers)
        return DecisionBatch('Return one opinion choice based on the provided peer list.',
            {qid:dict(type='choice',instructions=text,criteria={x:f'Support {x}.' for x in labels})},{qid:selected})

    def advance(self,t,actions,probabilities):
        if self.prepared is None or self.prepared[0]!=t: raise ValueError('Prepare first.')
        _,a,mapping,_=self.prepared; action=actions[f't{t}_a{a}']
        self.opinions[a]=next(x for x,label in mapping.items() if label==action)
        self.round=t; self.prepared=None
        m=sum(self.opinions)/self.n
        return dict(update=t,population_time=t/self.n,mean_opinion=m,coordination=abs(m),consensus=abs(m)==1)
