"""Mesa bridge plus a working organization-learning example (Mesa 3.5.1)."""
import hashlib
import json
import mesa
from mesa import Agent, Model
from mesa.datacollection import DataCollector
from . import kernel
from .sdk import DecisionBatch, FunctionEngine
from .workforce import build_workforce, workforce_metadata
from .organization import (validate_config, memberships, contact_sets, effective_policy,
                           observation, question, shared_state, rule_probabilities, apply_round)


class MesaAdapter:
    """Use callbacks to attach an existing Mesa model to the decision runtime.

    prepare(model, t) returns a DecisionBatch without advancing simulated time.
    commit(model, t, actions, probabilities) performs one model step, then reports metrics.
    """
    def __init__(self, model, *, prepare, commit, metadata):
        if not isinstance(model, Model):
            raise TypeError('A Mesa Model is required.')
        self.model, self._prepare, self._commit = model, prepare, commit
        self.metadata = metadata

    def describe(self):
        return {**self.metadata, 'backend': 'mesa', 'mesa_version': mesa.__version__}

    def prepare(self, round_no):
        return self._prepare(self.model, round_no)

    def advance(self, round_no, actions, probabilities):
        return self._commit(self.model, round_no, actions, probabilities)


class Employee(Agent):
    def __init__(self, model, index):
        super().__init__(model)
        self.index = index

    @property
    def performance(self):
        return float(self.model.scores[self.model.world['positions'][self.index]])

    def decision(self, round_no):
        model = self.model
        return observation(model.world, model.scores, model.config, model.labels,
                           model.peers, self.index, round_no)


class OrganizationModel(Model):
    def __init__(self, config):
        self.config = validate_config(config)
        super().__init__(rng=self.config['seed'])
        c = self.config
        self.scores = kernel.landscape(c['seed'])
        self.labels = memberships(c)
        self.world = kernel.initialize(c['agents'], c['seed'],
                                      dict(id='organization', **effective_policy(c, 1)), c['engine'])
        self.world['workforce'] = build_workforce(c, self.labels)
        self.initial_hash = hashlib.sha256(json.dumps(self.world['positions']).encode()).hexdigest()
        self.landscape_hash = hashlib.sha256(self.scores.tobytes()).hexdigest()
        for index in range(c['agents']):
            Employee(self, index)
        self.datacollector = DataCollector(model_reporters={
            'gross_performance': lambda m: m.world['metrics'][-1]['gross_performance'],
            'explore_share': lambda m: m.world['metrics'][-1]['explore_share'],
            'department_gap': lambda m: m.world['metrics'][-1]['department_gap']})
        self.prepared_round = None

    def prepare_decisions(self, t):
        if t != len(self.world['metrics'])+1 or self.prepared_round is not None:
            raise ValueError('Prepare exactly one next round before committing it.')
        self.peers = contact_sets(self.config, self.labels, t)
        questions, ids = {}, {}
        for employee in self.agents:
            a = employee.index
            qid = f't{t}_a{a}'
            questions[qid] = question(employee.decision(t), self.config['seed'], t, a)
            ids[qid] = a
        self.prepared_round = t
        return DecisionBatch(shared_state(self.config['rounds']), questions, ids)

    def commit_decisions(self, t, actions, probabilities):
        if t != self.prepared_round:
            raise ValueError('Round does not match the prepared decisions.')
        self.pending_actions, self.pending_probabilities = actions, probabilities
        self.step()
        return self.world['metrics'][-1]

    def step(self):
        t = self.prepared_round
        if t is None:
            raise ValueError('Prepare decisions before stepping.')
        actions, probabilities = self.pending_actions, self.pending_probabilities
        qids = [f't{t}_a{a}' for a in range(self.config['agents'])]
        metric = apply_round(self.world, self.scores, self.config, self.labels, self.peers,
                             [actions[q] for q in qids], [probabilities[q] for q in qids], t)
        self.datacollector.collect(self)
        self.prepared_round = None
        return metric


def organization_adapter(config):
    model = OrganizationModel(config)
    return MesaAdapter(model, prepare=lambda m,t: m.prepare_decisions(t),
        commit=lambda m,t,a,p: m.commit_decisions(t,a,p),
        metadata=dict(scenario='nk_organization', config=model.config,
                      **workforce_metadata(model.config, model.world['workforce']),
                      initial_state_sha256=model.initial_hash, landscape_sha256=model.landscape_hash,
                      source='Barkoczi & Galesic (2016), 10.1038/ncomms13109; organization extension'))


def organization_rule(kind='best'):
    if kind not in ['best', 'conformity']:
        raise ValueError('Unknown rule.')
    return FunctionEngine(lambda state,q: rule_probabilities(
        json.loads(q['instructions'].split('\n', 1)[0]), kind), name=kind)
