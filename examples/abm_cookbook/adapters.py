"""Adapters around installed Mesa 3.5.1 example models, not copied upstream code.

The upstream Model, Agent, grid, outcome methods and Mesa clock are reused.
Only scheduling is split at explicit decision boundaries. Exact baseline checks
compare these adapters with independently instantiated, unmodified Mesa models.
"""
import hashlib
import inspect
import json
from pathlib import Path

import mesa
from mesa.examples.basic.boltzmann_wealth_model.model import BoltzmannWealth, BoltzmannScenario
from mesa.examples.basic.schelling.model import Schelling, SchellingScenario
from mesa.examples.advanced.pd_grid.model import PdGrid
from orgabm.sdk import DecisionBatch, FunctionEngine


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode()).hexdigest()


class CoupledWealth(BoltzmannWealth):
    def step(self):
        self._ordo_finish()


class CoupledSchelling(Schelling):
    def step(self):
        self._ordo_finish()


class CoupledPD(PdGrid):
    def step(self):
        self._ordo_finish()


def upstream_model(kind, config, *, coupled=False):
    if mesa.__version__ != '3.5.1':
        raise ValueError('These adapters target Mesa 3.5.1; verify source semantics before upgrading.')
    values = {k:v for k,v in config.items() if k not in ('rounds', 'seed')}
    if kind == 'wealth':
        return (CoupledWealth if coupled else BoltzmannWealth)(BoltzmannScenario(**values, rng=config['seed']))
    if kind == 'schelling':
        return (CoupledSchelling if coupled else Schelling)(SchellingScenario(**values, rng=config['seed']))
    if kind == 'cooperation':
        bonus = values.pop('defection_bonus')
        return (CoupledPD if coupled else PdGrid)(**values, rng=config['seed'],
            payoffs={('C','C'):1, ('C','D'):0, ('D','C'):bonus, ('D','D'):0})
    raise ValueError('Unknown upstream model.')


def snapshot(kind, model):
    agents=[]
    for a in model.agents:
        row=dict(id=a.unique_id, position=list(a.cell.coordinate))
        if kind == 'wealth': row.update(wealth=a.wealth)
        elif kind == 'schelling': row.update(type=a.type, happy=a.happy)
        else: row.update(move=a.move, next_move=a.next_move, score=a.score)
        agents.append(row)
    result=dict(steps=model.steps, time=model.time, agents=agents,
                python_rng_sha256=digest(model.random.getstate()),
                numpy_rng_sha256=digest(model.rng.bit_generator.state))
    if kind == 'schelling': result.update(happy=model.happy, running=model.running)
    return result


def metrics(kind, model, t):
    n=len(model.agents)
    result=dict(round=t, population=n, state_sha256=digest(snapshot(kind,model)))
    if kind == 'wealth':
        result.update(total_wealth=sum(a.wealth for a in model.agents),
                      minimum_wealth=min(a.wealth for a in model.agents), gini=model.gini)
    elif kind == 'schelling':
        same=edges=0
        for a in model.agents:
            for b in a.cell.get_neighborhood(radius=a.radius).agents:
                edges+=1; same+=int(a.type==b.type)
        result.update(happy_share=model.happy/n, same_type_neighbor_share=same/edges if edges else 0,
                      minority_count=sum(a.type==1 for a in model.agents))
    else:
        result.update(cooperation_share=sum(a.move=='C' for a in model.agents)/n,
                      mean_cumulative_score=sum(a.score for a in model.agents)/n)
    return result


class ExistingMesaEnvironment:
    """Public StagedEnvironment with upstream world mechanics.

    Wealth: random sequential activation, automatic movement before each transfer.
    Schelling: independent choices from cached start-of-round happiness, then
    native shuffled relocation and post-round happiness evaluation.
    PD: simultaneous or sequential strategies as selected in the source model.
    """
    def __init__(self, kind, config):
        self.kind, self.config = kind, dict(config)
        self.model = upstream_model(kind, config, coupled=True)
        self.model._ordo_finish = self._finish_native_round
        self.initial = snapshot(kind,self.model)
        self.trajectory=[]
        self.current=0; self.schedule=None; self.index=0; self.prepared=None
        self.order=[]; self.pending_agents={}
        if not len(self.model.agents): raise ValueError('Use a nonempty population.')
        if kind=='schelling' and not any(c.is_empty for c in self.model.grid.all_cells):
            raise ValueError('The Schelling relocation example needs an empty cell.')

    def describe(self):
        source={'wealth':BoltzmannWealth,'schelling':Schelling,'cooperation':PdGrid}[self.kind]
        files={}
        for cls in (source,type(next(iter(self.model.agents)))):
            path=inspect.getsourcefile(cls)
            with open(path,'rb') as stream: files[cls.__module__]=hashlib.sha256(stream.read()).hexdigest()
        return dict(scenario='existing_mesa_'+self.kind, backend='mesa', mesa_version=mesa.__version__,
                    upstream_class=source.__module__+'.'+source.__name__, upstream_source_hashes=files,
                    config=self.config, initial_state_sha256=digest(self.initial),
                    adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

    def stages(self,t):
        if self.schedule is not None or t!=self.current+1: raise ValueError('Finish the previous round first.')
        m=self.model
        if self.kind=='wealth':
            self.order=list(m.agents.shuffle())
            self.schedule=[f'{phase}_{i}' for i in range(len(self.order)) for phase in ('move','transfer')]
        elif self.kind=='cooperation' and m.activation_order!='Simultaneous':
            self.order=list(m.agents.shuffle()) if m.activation_order=='Random' else list(m.agents)
            self.schedule=[f'choice_{i}' for i in range(len(self.order))]
        else:
            self.schedule=['choices']
            if self.kind=='schelling': m.happy=0
        self.index=0
        return list(self.schedule)

    def _check(self,t,stage):
        if t!=self.current+1 or self.schedule is None or self.index>=len(self.schedule) or stage!=self.schedule[self.index]:
            raise ValueError('Stages must preserve the upstream activation order.')

    def prepare_stage(self,t,stage):
        self._check(t,stage)
        if self.prepared is not None: raise ValueError('Commit the prepared stage first.')
        self.prepared=stage
        questions,ids,self.pending_agents={},{},{}
        if self.kind=='wealth':
            a=self.order[int(stage.split('_')[1])]
            actors=[] if stage.startswith('move') else [a]
        elif self.kind=='cooperation' and self.model.activation_order!='Simultaneous':
            actors=[self.order[self.index]]
        else: actors=list(self.model.agents)
        for a in actors:
            qid=f't{t}_{stage}_a{a.unique_id}'
            if self.kind=='wealth':
                peers=[b for b in a.cell.agents if b is not a]
                if a.wealth<=0 or not peers: continue
                criteria={f'to_{b.unique_id}':f'Transfer one unit to member {b.unique_id}.' for b in peers}
                observation=dict(own_wealth=a.wealth,
                    cellmates=[dict(id=b.unique_id,wealth=b.wealth) for b in peers])
            elif self.kind=='schelling':
                peers=list(a.cell.get_neighborhood(radius=a.radius).agents)
                criteria={'stay':'Remain at this location.','move':'Relocate to a randomly chosen empty cell.'}
                observation=dict(type=a.type, homophily=a.homophily, happy_at_round_start=a.happy,
                    neighbor_types=[b.type for b in peers], position=list(a.cell.coordinate))
            else:
                peers=[*list(a.cell.neighborhood.agents),a]
                criteria={'C':'Cooperate.','D':'Defect.'}
                observation=dict(own_move=a.move, own_score=a.score,
                    candidate_models=[dict(id=b.unique_id,move=b.move,score=b.score) for b in peers],
                    defection_bonus=self.config['defection_bonus'])
            questions[qid]=dict(type='choice',instructions=json.dumps(observation),criteria=criteria)
            ids[qid]=a.unique_id; self.pending_agents[qid]=a
        state={
            'wealth':'Predict the recipient of a mandatory one-unit transfer in a mechanistic wealth-exchange ABM. Movement, eligibility and wealth settlement are controlled by the environment. Use only the local record.',
            'schelling':'Predict whether a resident stays or moves in this Schelling-style ABM. Types are anonymous synthetic groups. Moving selects a random vacant cell, not a preferred destination. Decisions use start-of-round information; relocation follows afterward.',
            'cooperation':'Predict cooperation or defection in a repeated spatial game. Payoffs: C/C=1, C/D=0, D/D=0, D/C=the supplied bonus. Candidate models list neighbors then self. Scores are cumulative. The environment preserves the stated activation regime.'}[self.kind]
        return DecisionBatch(state,questions,ids)

    def advance_stage(self,t,stage,actions,probabilities):
        self._check(t,stage)
        if self.prepared!=stage: raise ValueError('Prepare before committing.')
        if set(actions)!=set(self.pending_agents): raise ValueError('Actions do not match prepared agents.')
        events=[]
        if self.kind=='wealth' and stage.startswith('move'):
            a=self.order[int(stage.split('_')[1])]; a.move()
            events.append(dict(event='automatic_move',agent=a.unique_id,position=list(a.cell.coordinate)))
        for qid,action in actions.items():
            a=self.pending_agents[qid]
            if self.kind=='wealth':
                target=int(action.split('_')[1])
                b=next((b for b in a.cell.agents if b is not a and b.unique_id==target),None)
                if a.wealth<=0 or b is None: raise ValueError('Invalid transfer.')
                a.wealth-=1; b.wealth+=1
            elif self.kind=='schelling':
                # Relocations are committed in the same shuffled order as upstream.
                a._ordo_action=action
            else:
                a.next_move=action
                if self.model.activation_order!='Simultaneous': a.advance()
            events.append(dict(event='decision',agent=a.unique_id,action=action))
        self.prepared=None; self.index+=1
        return dict(events=events)

    def _finish_native_round(self):
        m=self.model
        if self.kind=='schelling':
            for a in m.agents.shuffle():
                if a._ordo_action=='move': a.cell=m.grid.select_random_empty_cell()
            m.agents.do('assign_state')
            m.running=m.happy<len(m.agents)
        elif self.kind=='cooperation' and m.activation_order=='Simultaneous':
            m.agents.do('advance')
        m.datacollector.collect(m)

    def finish_round(self,t):
        if self.prepared is not None or self.schedule is None or self.index!=len(self.schedule) or t!=self.current+1:
            raise ValueError('Complete all stages first.')
        self.model.step()  # Retains Mesa's own clock, step and scheduled-event processing.
        self.current=t; self.schedule=None
        snap=snapshot(self.kind,self.model); self.trajectory.append(snap)
        result=metrics(self.kind,self.model,t)
        if self.kind=='wealth':
            assert result['total_wealth']==self.config['n'] and result['minimum_wealth']>=0
        if self.kind=='schelling':
            assert len({tuple(x['position']) for x in snap['agents']})==len(snap['agents'])
        return result

    def native_engine(self):
        def choose(state,question):
            obs=json.loads(question['instructions'])
            if self.kind=='wealth':
                # Capture the exact upstream RNG realization as a one-hot decision.
                action=self.model.random.choice(list(question['criteria']))
            elif self.kind=='schelling': action='stay' if obs['happy_at_round_start'] else 'move'
            else: action=max(obs['candidate_models'],key=lambda x:x['score'])['move']
            return {a:float(a==action) for a in question['criteria']}
        return FunctionEngine(choose,name='upstream-rule-'+self.kind)


def direct_reference(kind,config):
    model=upstream_model(kind,config)
    initial=snapshot(kind,model); states=[]; trajectory=[]
    for t in range(1,config['rounds']+1):
        model.step(); states.append(snapshot(kind,model)); trajectory.append(metrics(kind,model,t))
    return dict(initial=initial,states=states,metrics=trajectory)
