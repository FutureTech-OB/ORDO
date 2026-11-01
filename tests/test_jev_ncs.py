import unittest
from pathlib import Path
from examples.jev_ncs.models import CollectiveMobility,Colocation,DynamicGame,RuleEngine
from examples.jev_ncs.suite import build_cases,summarize,contrasts
from orgabm.sdk import run_simulation


@unittest.skipUnless(
    Path('.buildtmp/ncs-mobility-native/main.cpp').exists()
    and Path('.buildtmp/ncs-colocation-source/code/SimulationsSubmission.ipynb').exists()
    and Path('.buildtmp/ncs-dynamic-games/author-release.zip').exists(),
    'Optional pinned mobility, colocation, and dynamic-game sources not cached.')
class JevNCS(unittest.TestCase):
    def test_plan_counts_and_substantive_choices(self):
        cases=build_cases();self.assertEqual(len(cases),14)
        self.assertEqual(sum(c['rounds']*(16 if c['paper_id']!='ncs_dynamic_2026' else 1) for c in cases),2008)
        self.assertEqual(len({c['paper_id'] for c in cases}),3)
        for c in cases:
            batch=c['environment'].prepare(1)
            if not batch.questions:
                self.assertEqual(c['paper_id'],'ncs_dynamic_2026');self.assertIsNotNone(c['environment'].automatic_parent)
            self.assertTrue(all(len(q['criteria'])>=2 for q in batch.questions.values()))
            # Native likelihoods and target aggregate results are never questions.
            self.assertNotIn('predeclared_direction',str(batch))
            self.assertNotIn('baseline_probability',str(batch))

    def test_invalid_actions_atomic(self):
        for env in (CollectiveMobility(),Colocation(),DynamicGame()):
            batch=env.prepare(1);actions={q:'invalid' for q in batch.questions}
            with self.assertRaises(ValueError):env.advance(1,actions,{})
            self.assertEqual(env.round,0);self.assertEqual(env.records,[])

    def test_rule_baselines_run_and_conserve(self):
        for env in (CollectiveMobility(),Colocation(),DynamicGame()):
            result=run_simulation(env,RuleEngine(env),rounds=6,seed=7)
            self.assertEqual(result['status'],'complete');self.assertTrue(all(m['population']==result['metrics'][0]['population'] for m in result['metrics']))
            self.assertTrue(all(0<=p<=1 for probabilities in env.rules.values() for p in probabilities.values()))

    def test_dynamic_parent_is_neighbor_and_source_is_copied(self):
        env=DynamicGame(mutation=0);batch=env.prepare(1);q=next(iter(batch.questions));item=env.pending[q]
        action=next(iter(item['choices']));parent=item['choices'][action];old=list(env.state)
        self.assertIn(parent,env.graphs[env.network][item['death']]);env.advance(1,{q:action},{})
        self.assertEqual(env.state[item['death']],old[parent])
        self.assertEqual([env.state[i] for i in range(env.n) if i!=item['death']],[old[i] for i in range(env.n) if i!=item['death']])


if __name__=='__main__':unittest.main()
