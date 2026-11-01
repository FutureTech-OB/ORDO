"""Well-mixed imitation, preserving the author's sequential refresh semantics.

The payoff table is an intrinsic explicit-rule model component, not cached Jev
probabilities. Supplied trained strategies are evaluated, not retrained here.
"""
import ast
import copy
import math
from pathlib import Path
import random
import warnings
import numpy as np

from orgabm.sdk import DecisionBatch
from .model import DOI,COMMIT,NAMES,digest,source_manifest


class StrategyToken:
    def __init__(self,index):self.index=index
    def typeagent(self):return self.index


def author_generation(namespace):
    """Compile reviewed original inner-generation statements, omitting plotting/I/O."""
    source_manifest()
    text=(Path(__file__).parent/'upstream'/'author_well_mixed.py').read_text(encoding='utf-8')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',SyntaxWarning);tree=ast.parse(text)
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    loop=next(n for n in ast.walk(main) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='iepisode')
    body=[]
    for statement in loop.body:
        # Omit the source's whole-experiment metric buffers; preserve games/refresh.
        if isinstance(statement,ast.Assign) and any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name)
            and t.value.id in ('avg_reward_total','avg_cooprate_total') for t in statement.targets):continue
        body.append(statement)
        if isinstance(statement,ast.For) and isinstance(statement.target,ast.Name) and statement.target.id=='irefresh':break
    if not isinstance(body[-1],ast.For) or body[-1].target.id!='irefresh':raise ValueError('Author refresh loop unavailable.')
    wrapper=ast.parse('def generation(bigpopulation,strategy0729payoffmatrix,strategy0729cooprate,s):\n    pass\n').body[0]
    wrapper.body=body+ast.parse('return bigpopulation,avg_reward,avg_cooprate').body
    module=ast.fix_missing_locations(ast.Module(body=[wrapper],type_ignores=[]))
    exec(compile(module,'pinned_author_generation','exec'),namespace)
    return namespace['generation']


class WellMixedEvolution:
    def __init__(self,payoffs,cooperation,strategy_ids,*,agents=64,rounds=50,selection=.05,seed=7,with_mtbr=True):
        if type(agents) is not int or not 4<=agents<=2000:raise ValueError('Use 4..2,000 members.')
        if type(rounds) is not int or not 1<=rounds<=1000:raise ValueError('Use 1..1,000 generations.')
        if not 0<=selection<=10:raise ValueError('Selection intensity outside bounds.')
        self.payoffs=np.array(payoffs,dtype=float);self.cooperation=np.array(cooperation,dtype=float)
        if self.payoffs.shape!=(len(strategy_ids),len(strategy_ids)) or self.cooperation.shape!=self.payoffs.shape:
            raise ValueError('Strategy table dimensions differ.')
        self.strategy_ids=list(strategy_ids);self.n=agents;self.rounds=rounds;self.selection=selection;self.seed=seed
        self.with_mtbr=with_mtbr;self.rng=random.Random(seed)
        choices=[i for i,s in enumerate(strategy_ids) if with_mtbr or s!=-1]
        self.types=[self.rng.choice(choices) for _ in range(agents)];self.initial=list(self.types)
        self.round=0;self.current_stage=-1;self.old_fitness=None;self.old_cooperation=None;self.pending=None
    def describe(self):
        return dict(model='nc_well_mixed_evolution',doi=DOI,commit=COMMIT,agents=self.n,rounds=self.rounds,
            selection=self.selection,seed=self.seed,with_mtbr=self.with_mtbr,
            strategies=[NAMES[s] for s in self.strategy_ids],payoff_table_sha256=digest(self.payoffs.tolist()),
            timing='shuffle; evaluate all-pair old-strategy payoffs; sequential in-place imitation with frozen payoffs',
            scope='reduced strategy/Monte Carlo evaluation, not paper training or complete figure reproduction')
    def stages(self,t):
        if t!=self.round+1:raise ValueError('Generation order changed.')
        return [str(i) for i in range(self.n)]
    def prepare_stage(self,t,stage):
        i=int(stage)
        if i==0:
            self.rng.shuffle(self.types)
            a=np.array(self.types)
            self.old_fitness=[float((self.payoffs[x,a].sum()-self.payoffs[x,x])/(self.n-1)) for x in a]
            self.old_cooperation=[float((self.cooperation[x,a].sum()-self.cooperation[x,x])/(self.n-1)) for x in a]
        if i!=self.current_stage+1:raise ValueError('Sequential refresh order changed.')
        j=self.rng.randint(0,self.n-1)
        p=1/(math.exp(self.selection*(self.old_fitness[i]-self.old_fitness[j]))+1)
        self.pending=dict(focal=i,opponent=j,adopt=self.rng.random()<p)
        qid=f't{t}_a{i}'
        import json
        question=dict(type='choice',instructions=json.dumps(dict(own_strategy=NAMES[self.strategy_ids[self.types[i]]],
            candidate_strategy=NAMES[self.strategy_ids[self.types[j]]],own_fitness=self.old_fitness[i],
            candidate_fitness=self.old_fitness[j],selection=self.selection)),criteria={'adopt':'Copy this candidate','stay':'Keep current strategy'})
        return DecisionBatch('Well-mixed imitation of a strategy after repeated-game payoff evaluation.',{qid:question},{qid:i})
    def advance_stage(self,t,stage,actions,probabilities):
        i=int(stage);j=self.pending['opponent'];qid=f't{t}_a{i}'
        if actions[qid]=='adopt':self.types[i]=self.types[j]
        elif actions[qid]!='stay':raise ValueError('Invalid imitation action.')
        self.current_stage=i;self.pending=None
        return dict(focal=i,candidate=j,new_type=self.types[i])
    def finish_round(self,t):
        if self.current_stage!=self.n-1:raise ValueError('Incomplete generation.')
        self.round=t;self.current_stage=-1
        return dict(round=t,population=self.n,counts={NAMES[s]:self.types.count(i) for i,s in enumerate(self.strategy_ids)},
            mean_payoff=sum(self.old_fitness)/self.n,mean_cooperation=sum(self.old_cooperation)/self.n,
            source_population_payoff=sum(self.old_fitness)/(self.n-1),state_sha256=digest(self.types))


class NativeImitation:
    def __init__(self,world):self.world=world
    def decide(self,state,questions):
        if len(questions)!=1:raise ValueError('Author refresh decisions are sequential.')
        choose=self.world.pending['adopt']
        return {qid:{'adopt':float(choose),'stay':float(not choose)} for qid in questions}
    def usage(self):return dict(engine='author-fermi-imitation',actual_model_api_calls=0,recorded_input_cost_usd=0)


def evolution_reference(world):
    rng=random.Random(world.seed)
    choices=[i for i,s in enumerate(world.strategy_ids) if world.with_mtbr or s!=-1]
    people=[StrategyToken(rng.choice(choices)) for _ in range(world.n)]
    namespace=dict(random=rng,np=np,exp=math.exp);generation=author_generation(namespace)
    rows=[]
    for t in range(1,world.rounds+1):
        people,fitness,cooperation=generation(people,world.payoffs,world.cooperation,world.selection)
        rows.append(dict(types=[p.typeagent() for p in people],fitness=list(fitness),cooperation=list(cooperation)))
    return rows
