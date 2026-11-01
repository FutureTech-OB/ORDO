import unittest
from examples.nc_additional_games.model import SocialRewarding,NativeEngine,direct_reference,source_manifest
from orgabm.sdk import run_simulation


class NCSocialRewarding(unittest.TestCase):
    def test_full_individual_state_and_cooperation_match_author_loop(self):
        for information in (0,1):
            for mutation in (0,.1):
                for seed in (7,8):
                    world=SocialRewarding(agents=20,rounds=80,information=information,mutation=mutation,seed=seed)
                    reference=direct_reference(world.config)
                    result=run_simulation(world,NativeEngine(world),rounds=80,seed=seed)
                    for row,ref in zip(result['metrics'],reference):
                        for k,v in ref.items():self.assertEqual(row[k],v)
                        self.assertEqual(sum(row['post_strategy_counts'].values()),20)
    def test_homogeneous_cooperation_and_payoff_cases(self):
        for information in (0,.5,1):
            world=SocialRewarding(information=information)
            ns=world.ns
            counts={i:0 for i in range(16)}
            counts[0]=100;self.assertEqual(ns['get_coop_rate'](counts),1)
            counts[0]=0;counts[12]=100;self.assertEqual(ns['get_coop_rate'](counts),0)
            if information==1:
                counts[12]=0;counts[5]=100;self.assertEqual(ns['get_coop_rate'](counts),1)
                payoff=ns['get_avg_payoff'](1,1,ns['payoff_A'],ns['payoff_B'],{0:0,1:100,2:0,3:0},{0:0,1:100,2:0,3:0})
                self.assertAlmostEqual(payoff,2.5)
        self.assertEqual(source_manifest()['git_blob_sha'],'7723518b117b89ff7e33a20c527b217337d8ed92')
    def test_invalid_decision_does_not_commit_native_shadow_state(self):
        class Bad:
            def decide(self,state,q):return {}
            def usage(self):return {}
        world=SocialRewarding(rounds=1);before=world.snapshot()
        import copy
        before=copy.deepcopy(before)
        with self.assertRaises(ValueError):run_simulation(world,Bad(),rounds=1,seed=7)
        self.assertEqual(world.snapshot(),before)


if __name__=='__main__':unittest.main()
