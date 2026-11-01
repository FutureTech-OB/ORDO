"""Offline native-loop comparisons; no network, credentials or LLM outputs."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from .environment import FloodEnvironment, native_reference, locked_source, UPSTREAM
from .suite import build_cases


def chooser(mode):
    def choose(prompt, index):
        elevated = 'Your house is already elevated' in prompt
        if mode == 'inaction':
            return '3' if elevated else '4'
        if mode == 'relocate':
            return '2' if elevated else '3'
        if mode == 'elevate':
            return '1' if elevated else '2'
        return str(1+(index*7+index//17) % (3 if elevated else 4))
    return choose


def run_adapter(seed, choose, reverse_probabilities=False):
    e = FloodEnvironment(seed)
    prompts = []
    metrics = []
    for year in range(1, 11):
        batch = e.prepare(year)
        actions, probabilities = {}, {}
        for qid,q in batch.questions.items():
            code = str(choose(q['instructions'], len(prompts)))
            prompts.append(q['instructions'])
            actions[qid] = code
            probabilities[qid] = {key:float(key == code) for key in q['criteria']}
        if reverse_probabilities:
            probabilities = dict(reversed(list(probabilities.items())))
        metrics.append(e.advance(year, actions, probabilities))
    return e, prompts, metrics


class MechanicsTest(unittest.TestCase):
    def test_pinned_blob_and_license(self):
        self.assertIn('run_simulation', locked_source())
        self.assertIn('Redistribution and use', (UPSTREAM/'LICENSE').read_text())

    def test_author_loop_exact(self):
        """36 complete 100-household protocols, including early terminal worlds."""
        for seed in (0, 1, 7, 19, 20261030, 20261079, 20261100, 982, 233):
            for mode in ('inaction', 'relocate', 'elevate', 'mixed'):
                with self.subTest(seed=seed, mode=mode):
                    choose = chooser(mode)
                    ref = native_reference(seed, choose)
                    adapter, prompts, metrics = run_adapter(seed, choose)
                    self.assertEqual(ref['prompts'], prompts)
                    self.assertEqual(ref['agents'], adapter.agents)
                    self.assertEqual(ref['logs'], adapter.logs)
                    self.assertEqual(ref['flood_years'], [3, 4, 9])
                    self.assertEqual(len(adapter.agents), 100)
                    for a in adapter.agents:
                        self.assertLessEqual(a['trust_in_insurance'], 1)
                        self.assertGreaterEqual(a['trust_in_neighbors'], 0)
                        self.assertTrue(all(not x for x in a['threat_appraisals']))

    def test_complete_plan_without_shrinking(self):
        cases = build_cases()
        self.assertEqual(len(cases), 50)
        self.assertEqual(len(set(c['seed'] for c in cases)), 50)
        self.assertTrue(all(c['rounds'] == 10 and c['environment'].describe()['agents'] == 100 for c in cases))
        self.assertTrue(all(c['environment'].describe()['flood_years'] == [3, 4, 9] for c in cases))

    def test_no_appraisal_feedback_or_private_other_agents(self):
        env = FloodEnvironment(7)
        batch = env.prepare(1)
        for qid,q in batch.questions.items():
            self.assertNotIn('flood_threshold', q['instructions'])
            self.assertNotIn('trust_in_insurance', q['instructions'])
            self.assertNotIn('raw_llm_decision', q['instructions'])
            self.assertIn('1', q['criteria'])
        ns = env.ns
        # The original function reads/writes no appraisals in any future prompt.
        self.assertNotIn('threat_appraisals', ns['prompt_template'])

    def test_relocated_never_decides_again(self):
        env, prompts, metrics = run_adapter(1, chooser('relocate'))
        self.assertEqual(len(prompts), 100)
        self.assertEqual(metrics[-1]['adaptation_counts']['Relocate'], 100)
        self.assertEqual(metrics[-1]['actual_source_years'], 1)
        self.assertTrue(all(m['active_decisions'] == 0 for m in metrics[1:]))

    def test_logged_reasons_do_not_change_future_inputs(self):
        a = native_reference(20261030,chooser('mixed'))
        b = native_reference(20261030,chooser('mixed'),appraisals=True)
        self.assertEqual(a['prompts'],b['prompts'])
        for left,right in zip(a['agents'],b['agents']):
            for key in left:
                if key not in ('threat_appraisals','coping_appraisals'):
                    self.assertEqual(left[key],right[key])
        self.assertNotEqual(a['agents'][0]['threat_appraisals'],b['agents'][0]['threat_appraisals'])

    def test_probabilities_are_keyed_not_ordered(self):
        a, _, m1 = run_adapter(9, chooser('mixed'))
        b, _, m2 = run_adapter(9, chooser('mixed'), reverse_probabilities=True)
        self.assertEqual(a.agents,b.agents)
        self.assertEqual(m1,m2)


if __name__ == '__main__':
    unittest.main()
