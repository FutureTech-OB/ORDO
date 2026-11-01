"""Public SDK boundary around the author's unmodified foraging mechanics."""
import copy
import hashlib
import json
import math
import numpy as np
from orgabm.sdk import DecisionBatch


def plain(value):
    if isinstance(value,np.ndarray):return plain(value.tolist())
    if isinstance(value,np.generic):return plain(value.item())
    if isinstance(value,float) and not math.isfinite(value):return None
    if isinstance(value,dict):return {str(k):plain(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [plain(x) for x in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(plain(value),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def state_record(state):
    return {key:plain(value) for key,value in state.__dict__.items()}


def slice_record(snapshot):
    return dict(step=snapshot.step,state=state_record(snapshot.state),
        views=[plain(x.__dict__) for x in snapshot.agent_views],states=plain(snapshot.agent_states))


POLICIES={
    'asocial':dict(dist_weight=-1,in_view_weight=1,gp_weight=1,any_social_weight=0,success_social_weight=0),
    'unbiased_social':dict(dist_weight=-1,in_view_weight=1,gp_weight=1,any_social_weight=1,success_social_weight=0),
    'success_biased_social':dict(dist_weight=-1,in_view_weight=1,gp_weight=1,any_social_weight=0,success_social_weight=1)}


class ForagingEnvironment:
    def __init__(self,task_module,simulation_module,cache,*,environment='smooth',policy='asocial',
                 seed=7,agents=4,steps=400,mining_steps=9):
        if environment not in ('smooth','random') or policy not in POLICIES:raise ValueError('Unknown environment/policy.')
        if type(agents) is not int or not 1<=agents<=16 or type(steps) is not int or not 1<=steps<=1000:
            raise ValueError('Use 1..16 agents and 1..1,000 physical steps.')
        self.config=dict(environment=environment,policy=policy,seed=seed,agents=agents,steps=steps,mining_steps=mining_steps)
        self.initial=task_module.State.from_env_file(str(__import__('pathlib').Path(cache)/f'{environment}.1.csv'),seed=seed,n_agents=agents)
        self.policy=simulation_module.Policy(**POLICIES[policy]);self.module=simulation_module
        self.sim=simulation_module.Simulation(agent_policies=[self.policy]*agents,initial_state=self.initial,
            max_steps=steps,mining_steps=mining_steps)
        self.generator=simulation_module.run_generator(self.sim,seed=seed,sim_slice_rate=1)
        self.pending=None;self.final_result=None;self.done_metrics=None;self.round=0;self.decisions=0
        self.current=next(self.generator);self.initial_sha256=digest(state_record(self.initial))

    def describe(self):
        return dict(scenario='published_collective_foraging',doi='10.1038/s41467-025-58365-6',**self.config,
            initial_state_sha256=self.initial_sha256,
            observation='Author AgentView; visible rewards and remembered visible players; author shared revealed-map mask.',
            scheduling='Original author run loop, paused at one goal-selection call; mechanical navigation/mining unchanged.',
            native_sampling='Author PCG64 stochastic policy chooses once; one-hot action recording preserves original RNG stream.',
            horizon='agents*steps safe goal-choice upper bound; terminal empty SDK rounds are padding, not physical time.')

    def prepare(self,t):
        if self.pending is not None or t!=self.round+1:raise ValueError('Commit previous decision first.')
        if self.final_result is not None:
            self.pending={};return DecisionBatch('Completed foraging world.',{}, {})
        step,a,view,state,policy,rng=self.current
        eligible=np.argwhere(~state.revealed_map)
        choices={f'cell_{int(x)}_{int(y)}':f'Forage at ({int(x)},{int(y)}).' for x,y in eligible}
        known=np.argwhere(~np.isnan(view.agent_rewards_map))
        observed=[dict(x=int(x),y=int(y),reward=int(view.agent_rewards_map[x,y])) for x,y in known]
        record=dict(physical_step=step,agent=a,observed_rewards=observed,visible_or_remembered_positions=plain(view.agent_locs),
            visible_or_remembered_directions=plain(view.agent_dirs),rewarded_partners=plain(view.rewarded_agents),policy=POLICIES[self.config['policy']])
        qid=f'decision{t}_agent{a}';self.pending={qid:choices}
        return DecisionBatch('Choose the next unrevealed resource cell using this member\'s author-defined local view.',
            {qid:dict(type='choice',instructions=json.dumps(record,separators=(',',':')),criteria=choices)},{qid:a})

    def advance(self,t,actions,probabilities):
        if self.pending is None:raise ValueError('Prepare first.')
        if self.final_result is None:
            qid=next(iter(self.pending));key=actions[qid]
            if key not in self.pending[qid]:raise ValueError('Illegal foraging goal.')
            _,x,y=key.split('_');self.decisions+=1
            try:self.current=self.generator.send((int(x),int(y)))
            except StopIteration as stop:self.final_result=stop.value;self.current=None
        self.round=t;self.pending=None
        if self.final_result is not None:
            if self.done_metrics is None:
                result=self.final_result;snapshot=result.sim_slices[-1]
                self.done_metrics=dict(complete=True,physical_steps=len(result.stats)//self.config['agents'],
                    cumulative_reward=sum(int(x['reward']) for x in result.stats),revealed=int(snapshot.state.revealed_map.sum()),
                    state_sha256=digest(slice_record(snapshot)),goal_decisions=self.decisions)
            return dict(round=t,**self.done_metrics)
        step,a,view,state,policy,rng=self.current
        return dict(round=t,complete=False,physical_step=step,state_sha256=digest(state_record(state)),goal_decisions=self.decisions)

    def reference(self):
        # This calls the original unmodified author Simulation.run method.
        return self.sim.run(seed=self.config['seed'],sim_slice_rate=1)


class AuthorPolicyEngine:
    def __init__(self,environment):self.environment=environment
    def decide(self,state,questions):
        if not questions:return {}
        step,a,view,world,policy,rng=self.environment.current
        goal=policy.sample_next_cell(view,world,rng=rng);chosen=f'cell_{int(goal[0])}_{int(goal[1])}'
        return {q:{k:float(k==chosen) for k in row['criteria']} for q,row in questions.items()}
    def usage(self):return dict(engine='unmodified-author-policy-PCG64',actual_model_api_calls=0,recorded_input_cost_usd=0)
