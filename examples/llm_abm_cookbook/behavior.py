"""Fresh behavioral tests of published interaction protocols, not archive replay.

One ensemble step prepares one next update from every independent active world.
All questions receive fresh engine inference; finished worlds submit no questions.
"""
from collections import Counter
import copy
import json
import random

from orgabm.sdk import DecisionBatch
from .environments import NamingGame, MajorityOpinion, digest


class PaperNamingGame(NamingGame):
    def __init__(self,*,options=('Q','M'),seed=7,initial=None,committed=0,target='M'):
        super().__init__(agents=24,options=options,memory_size=5,seed=seed)
        if initial is not None:
            if initial not in options or target not in options or target==initial or not 0<=committed<self.n:
                raise ValueError('Specify distinct initial/target names and a legal committed count.')
            for row in self.agents.values():
                row.update(my_history=[initial]*5,partner_history=[initial]*5,
                    outcome=[100]*5,score_history=[100,200,300,400,500],score=500)
            for a in random.Random(seed+991).sample(list(self.agents),committed):
                self.agents[a]['committed_tag']=True
            self.committed_to=target
        elif committed:
            raise ValueError('Committed treatment requires a pre-established convention.')
        self.initial_convention=initial; self.target=target if initial is not None else None
        self.committed_count=committed; self.initial_sha256=digest(self.agents)

    def describe(self):
        return dict(super().describe(),prompt_version='paper-semantic-v1',
            mode='fresh_engine',initial_convention=self.initial_convention,
            committed_agents=self.committed_count,target=self.target,
            adaptation='source game framing/history, typed probability output instead of chain-of-thought text')

    def prepare(self,t):
        batch=super().prepare(t)
        for qid,question in batch.questions.items():
            a=batch.agent_ids[qid]; view=self.local_view(a)
            names=list(question['criteria'])
            history=[{'round':r['round'],'Player 1':r['own'],'Player 2':r['partner'],'payoff':r['payoff']}
                     for r in view['history']]
            question['instructions']=(
                f'Player 1 and Player 2 play a partnership game described as lasting 100 rounds. '
                f'On each round both simultaneously choose an action from {names}. '
                'If the actions agree, both receive +100 points; otherwise both receive -50 points. '
                'Each player aims to maximize their accumulated points, conditional on the other player\'s behavior. '
                f'Recent personal rounds: {json.dumps(history)}. '
                f'It is now local round {len(history)+1}; Player 1\'s score over the displayed rounds is {view["local_score"]}. '
                'Which action should Player 1 play? Consider the displayed history.')
        return batch


def naming_summary(world):
    window=world.events[-3*world.n:]
    counts=Counter(x for e in window for x in e['answers'])
    mutable=[]
    for event in window:
        mutable.extend(x for a,x in zip(event['players'],event['answers']) if not world.agents[a]['committed_tag'])
    dominant=counts.most_common(1)[0] if counts else (None,0)
    success=sum(e['outcome'] for e in window)/len(window) if window else 0
    return dict(updates=world.round,population_rounds=world.round/world.n,window_interactions=len(window),
        success=success,dominant=dominant[0],dominant_share=dominant[1]/sum(counts.values()) if counts else 0,
        target_share=counts.get(world.target,0)/sum(counts.values()) if counts and world.target else None,
        mutable_target_share=mutable.count(world.target)/len(mutable) if mutable and world.target else None,
        fixed_agents=world.committed_count)


class IndependentWorlds:
    """Environment adapter for parallel independent worlds behind the public SDK."""
    def __init__(self,worlds,configurations,*,max_updates,progress=None):
        self.worlds=worlds; self.configurations=configurations; self.max_updates=max_updates
        self.progress=progress; self.finished={}; self.pending={}; self.metrics={}
        self.first_target_window={}; self.first_consensus={}

    def describe(self):
        return dict(scenario='independent_published_ABM_worlds',worlds=self.configurations,
            max_updates=self.max_updates,probability_reuse=False,
            batching='one causally ready update per independent world; then barrier before the next update',
            sampling='public SDK seeded action draws; world-prefixed unique actor IDs; not paired CRN across conditions')

    def prepare(self,t):
        self.pending={}; questions={}; agents={}; states=set()
        for wid,world in self.worlds.items():
            if wid in self.finished: continue
            if world.round>=self.max_updates[wid]:
                self.finished[wid]='horizon'; continue
            batch=world.prepare(world.round+1); states.add(batch.state)
            translation={f'{wid}__{qid}':qid for qid in batch.questions}
            questions.update({key:batch.questions[qid] for key,qid in translation.items()})
            agents.update({key:(wid,batch.agent_ids[qid]) for key,qid in translation.items()})
            self.pending[wid]=(translation,batch)
        if len(states)>1: raise ValueError('An ensemble must share the same engine state framing.')
        return DecisionBatch(next(iter(states)) if states else 'All worlds finished.',questions,agents)

    def advance(self,t,actions,probabilities):
        updated={}
        for wid,(mapping,batch) in self.pending.items():
            world=self.worlds[wid]
            local_actions={qid:actions[key] for key,qid in mapping.items()}
            local_probs={qid:probabilities[key] for key,qid in mapping.items()}
            row=world.advance(world.round+1,local_actions,local_probs)
            if isinstance(world,PaperNamingGame):
                s=naming_summary(world); row.update(s)
                enough=s['window_interactions']>=3*world.n
                if world.target is None:
                    if enough and s['success']==1 and s['dominant_share']>=.95:
                        self.finished[wid]='spontaneous_convention'; self.first_consensus[wid]=world.round
                else:
                    if enough and s['success']>=.95 and s['mutable_target_share'] is not None and s['mutable_target_share']>=.95:
                        # Continue to the fixed horizon: a first tipping window need not remain stable.
                        self.first_target_window.setdefault(wid,world.round)
            elif row['consensus']:
                self.finished[wid]='consensus'; self.first_consensus[wid]=world.round
            if world.round>=self.max_updates[wid] and wid not in self.finished:
                self.finished[wid]='horizon'
            self.metrics[wid]=row; updated[wid]=row
        if self.progress and (t==1 or t%25==0):
            self.progress(dict(step=t,active=len(self.worlds)-len(self.finished),finished=len(self.finished)))
        return dict(step=t,worlds=updated,active=len(self.worlds)-len(self.finished))

    def summaries(self):
        rows=[]
        for wid,world in self.worlds.items():
            row=dict(self.configurations[wid],world=wid,updates=world.round,stop=self.finished.get(wid,'incomplete'),
                     first_target_window_update=self.first_target_window.get(wid),
                     first_consensus_update=self.first_consensus.get(wid),last=self.metrics.get(wid),
                     environment=world.describe())
            if isinstance(world,PaperNamingGame): row['final_individual_state_sha256']=digest(world.agents)
            else: row['final_opinions']=list(world.opinions)
            rows.append(row)
        return rows


def make_naming_worlds():
    worlds={}; configs={}; limits={}; serial=0
    for options in (list('QMXYFJPRCD'),['Q','M']):
        for repeat in range(4):
            wid=f'w{serial}'; seed=1001+serial; serial+=1
            worlds[wid]=PaperNamingGame(options=options,seed=seed)
            configs[wid]=dict(family='naming',condition=f'spontaneous_W{len(options)}',repeat=repeat,seed=seed)
            limits[wid]=1000
    for committed in (0,4,5,8):
        for repeat in range(3):
            wid=f'w{serial}'; seed=1001+serial; serial+=1
            worlds[wid]=PaperNamingGame(seed=seed,initial='Q',target='M',committed=committed)
            configs[wid]=dict(family='naming',condition=f'Q_to_M_{committed}',repeat=repeat,seed=seed,
                              committed=committed,initial='Q',target='M')
            limits[wid]=1000
    return IndependentWorlds(worlds,configs,max_updates=limits)


def make_opinion_worlds():
    worlds={}; configs={}; limits={}; serial=0
    for n,repeats in ((10,3),(50,10),(100,3)):
        for repeat in range(repeats):
            wid=f'w{serial}'; seed=3001+serial; serial+=1
            worlds[wid]=MajorityOpinion(agents=n,seed=seed)
            configs[wid]=dict(family='opinion',condition=f'N{n}',agents=n,repeat=repeat,seed=seed)
            limits[wid]=10*n
    return IndependentWorlds(worlds,configs,max_updates=limits)
