import json
import unittest
import warnings
from pathlib import Path
from orgabm.sdk import run_simulation,FunctionEngine
from examples.jev_nc.environments import FreshRepeatedGame,FreshSocialRewarding,FreshForaging,foraging_modules
from examples.jev_nc.suite import build_cases,analyze


def first(state,question):
    keys=list(question['criteria']);return {k:float(k==keys[0]) for k in keys}


class FreshNC(unittest.TestCase):
    def test_repeated_game_uses_new_choices_and_private_feedback(self):
        world=FreshRepeatedGame(initial='CC',pairs=2,rounds=3)
        def defect(state,q):return {'C':0.,'D':1.}
        result=run_simulation(world,FunctionEngine(defect),rounds=3,seed=7)
        self.assertEqual(result['decisions'],12)
        self.assertEqual(result['metrics'][-1]['mean_cumulative_payoff'],3)
        self.assertEqual(result['metrics'][-1]['cooperation'],0)
        q=next(iter(world.prepare(4).questions.values()))
        record=json.loads(q['instructions'])
        self.assertEqual(len(record['prior_interactions']),4)
        self.assertNotIn('strategy',record)
        self.assertNotIn('native',q['instructions'])

    def test_rewarding_no_native_decision_and_true_counterfactual_payoff(self):
        world=FreshSocialRewarding(information=1,agents=16,rounds=2,mutation=1)
        world.ns['step']=lambda *a:(_ for _ in ()).throw(AssertionError('Author action must not run.'))
        batch=world.prepare(1)
        own_before=dict(world.donor)
        self.assertEqual(len(batch.questions),16)
        for q,(person,candidate) in world.pending.items():
            row=json.loads(batch.questions[q]['instructions']);d,r=candidate//4,candidate%4
            expected=sum(.5*(world.ns['payoff_A'][d,world.recipient[j]]+world.ns['payoff_B'][world.donor[j],r])
                for j in world.donor if j!=person)/15
            self.assertAlmostEqual(row['offered_expected_points'],expected)
            self.assertNotIn('fermi',batch.questions[q]['instructions'])
        self.assertEqual(world.donor,own_before)
        expected={person:candidate for person,candidate in world.pending.values()}
        metric=world.advance(1,{q:'adopt' for q in batch.questions},{q:{'keep':0,'adopt':1} for q in batch.questions})
        self.assertEqual({i:4*world.donor[i]+world.recipient[i] for i in world.donor},expected)
        self.assertTrue(0<=metric['cooperation']<=1)

    @unittest.skipUnless(Path('.buildtmp/nc-foraging-source/simulation.py').exists(),
                         'Optional pinned foraging sources not cached.')
    def test_foraging_hidden_rewards_do_not_leak_and_choices_drive_original_world(self):
        task,sim,cache=foraging_modules()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',RuntimeWarning)
            w1=FreshForaging(task,sim,cache,steps=35,seed=7)
            w2=FreshForaging(task,sim,cache,steps=35,seed=7)
            w2.current[3].rewards_map[:]=1-w2.current[3].rewards_map
            b1=w1.prepare(1);b2=w2.prepare(1)
            self.assertEqual(b1.questions,b2.questions)
            self.assertLessEqual(len(next(iter(b1.questions.values()))['criteria']),24)
            # A fresh world runs without ever sampling a native author policy.
            original=sim.Policy.sample_next_cell
            def forbidden(*a,**k):raise AssertionError('Native author policy must not run.')
            sim.Policy.sample_next_cell=forbidden
            try:
                world=FreshForaging(task,sim,cache,steps=35,seed=11)
                result=run_simulation(world,FunctionEngine(first),rounds=140,seed=11)
            finally:sim.Policy.sample_next_cell=original
        self.assertTrue(result['metrics'][-1]['complete'])
        self.assertGreater(result['decisions'],4)
        self.assertEqual(result['metrics'][-1]['physical_steps'],35)

    @unittest.skipUnless(Path('.buildtmp/nc-foraging-source/simulation.py').exists(),
                         'Optional pinned foraging sources not cached.')
    def test_build_cases_and_analysis_do_not_preset_success(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',RuntimeWarning)
            cases=build_cases()
        self.assertEqual(len(cases),20)
        self.assertEqual(len({x['id'] for x in cases}),20)
        self.assertEqual(len({x['paper_id'] for x in cases}),3)
        results=[]
        for case in cases[:6]:
            w=case['environment']
            result=run_simulation(w,FunctionEngine(lambda s,q:{'C':0.,'D':1.}),rounds=case['rounds'],seed=case['seed'])
            results.append(dict(case,result=result))
        report=analyze(results)
        self.assertFalse(report['papers']['nc_repeated_games']['supports_exploratory_recovery_pattern'])
        self.assertEqual(report['papers']['nc_social_rewarding']['status'],'no_results')
        json.dumps(report,allow_nan=False)


if __name__=='__main__':unittest.main()
