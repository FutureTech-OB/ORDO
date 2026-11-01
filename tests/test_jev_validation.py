import json
from pathlib import Path
import tempfile
import unittest

from examples.jev_validation.run import Ensemble, ExactReplay
from orgabm.sdk import DecisionBatch, FunctionEngine, run_simulation


class PrivateWorld:
    def __init__(self, secret):
        self.secret = secret
        self.value = 0

    def describe(self):
        return dict(secret=self.secret)

    def prepare(self, t):
        return DecisionBatch(self.secret, {f'q{t}': dict(type='choice',
            instructions=f'Current value {self.value}', criteria=dict(A='A', B='B'))},
            {f'q{t}': 'same-agent-id'})

    def advance(self, t, actions, probabilities):
        self.value += next(iter(actions.values())) == 'A'
        return dict(value=self.value)


def cases():
    return [dict(id=key, paper_id='demo', environment=PrivateWorld(secret), rounds=n,
                 seed=7, condition=key) for key, secret, n in [('x', 'PRIVATE_X', 3), ('y', 'PRIVATE_Y', 1)]]


class ValidationRunnerTests(unittest.TestCase):
    def test_independent_information_and_unequal_horizons(self):
        ensemble = Ensemble(cases())
        batch = ensemble.prepare(1)
        self.assertNotIn('PRIVATE_', batch.state)
        self.assertIn('PRIVATE_X', batch.questions['x::q1']['instructions'])
        self.assertNotIn('PRIVATE_Y', batch.questions['x::q1']['instructions'])
        self.assertEqual(len(set(batch.agent_ids.values())), 2)
        env = Ensemble(cases())
        live = run_simulation(env, FunctionEngine(lambda s, q: {'A': .5, 'B': .5}), rounds=3, seed=12)
        self.assertEqual(live['decisions'], 4)
        self.assertEqual([x['result']['completed_rounds'] for x in env.results()], [3, 1])

    def test_exact_input_replay_and_changed_inputs_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/'run'
            env = Ensemble(cases())
            live = run_simulation(env, FunctionEngine(lambda s, q: {'A': .6, 'B': .4}),
                                  rounds=3, seed=12, output=root)
            replay = Ensemble(cases())
            result = run_simulation(replay, ExactReplay(root/'events.jsonl'), rounds=3, seed=12)
            self.assertEqual(live['metrics'], result['metrics'])
            self.assertEqual(env.results(), replay.results())
            rows = [json.loads(line) for line in (root/'events.jsonl').read_text().splitlines()]
            rows[0]['questions']['x::q1']['instructions'] = 'changed'
            changed = Path(folder)/'changed.jsonl'
            changed.write_text('\n'.join(json.dumps(row) for row in rows))
            with self.assertRaises(ValueError):
                run_simulation(Ensemble(cases()), ExactReplay(changed), rounds=3, seed=12)
