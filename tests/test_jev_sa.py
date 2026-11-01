import json
import unittest
from examples.jev_sa.suite import FreshNaming,build_cases,analyze
from examples.jev_sa.pgg import PublicGoodsPC,make_neighbors,payoffs,fermi_engine
from orgabm.sdk import run_simulation


class JevSASuiteTests(unittest.TestCase):
    def test_case_coverage_and_independent_instances(self):
        cases=build_cases()
        self.assertEqual(len(cases),16)
        self.assertEqual(len({c['paper_id'] for c in cases}),3)
        self.assertEqual(len({c['id'] for c in cases}),16)
        self.assertEqual(len({id(c['environment']) for c in cases}),16)

    def test_pgg_overlapping_average_payoff(self):
        # Three-node star, only its center contributes: groups sizes 3,2,2.
        # r=3 => center avg=(0+.5+.5)/3; each leaf avg=(1+1.5)/2.
        actual=payoffs([1,0,0],make_neighbors(3,'star'),3)
        self.assertAlmostEqual(actual[0],1/3)
        self.assertEqual(actual[1:],[1.25,1.25])
        self.assertEqual(payoffs([1,1,1],make_neighbors(3,'star'),3),[2,2,2])

    def test_pgg_absorption_and_local_information(self):
        world=PublicGoodsPC(seed=7,colonies=2)
        world.strategies=[[0]*10,[1]*10]
        batch=world.prepare(1);self.assertEqual(batch.questions,{})
        metrics=world.advance(1,{},{});self.assertEqual(metrics['active_colonies'],0)
        self.assertEqual(world.strategies,[[0]*10,[1]*10])
        other=PublicGoodsPC(seed=7,colonies=4)
        batch=other.prepare(1)
        self.assertTrue(batch.questions)
        for q in batch.questions.values():
            self.assertEqual(set(q['criteria']),{'keep','adopt'})
            self.assertNotIn('Fermi',q['instructions']);self.assertNotIn('threshold',q['instructions'])

    def test_naming_current_partner_choice_stays_hidden(self):
        world=FreshNaming(committed=5,seed=7)
        batch=world.prepare(1)
        for q in batch.questions.values():
            self.assertNotIn('committed',q['instructions'])
            self.assertNotIn('population',q['instructions'])
        self.assertEqual(sum(a['committed_tag'] for a in world.agents.values()),5)
        self.assertEqual(world.local_view(1)['local_score'],500)

    def test_unpaid_fermi_comparator_runs_real_feedback(self):
        world=PublicGoodsPC(seed=19,colonies=4)
        result=run_simulation(world,fermi_engine(),rounds=30,seed=19)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(len(result['metrics']),30)
        self.assertTrue(all(0<=m['cooperation_fraction']<=1 for m in result['metrics']))
        self.assertEqual(result['metrics'][-1]['monte_carlo_time'],3)


if __name__=='__main__':unittest.main()
