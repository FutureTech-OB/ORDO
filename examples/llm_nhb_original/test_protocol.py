"""Free protocol checks only; never calls an LLM/API."""
import unittest
from orgabm.sdk import run_simulation,FunctionEngine
from .suite import OriginalTournament,original_reference,GreedyDecisionEngine


class ProtocolTests(unittest.TestCase):
    def run_policy(self,choice):
        env=OriginalTournament();engine=FunctionEngine(lambda state,q:{'J':float(choice=='J'),'F':float(choice=='F')})
        result=run_simulation(env,engine,rounds=300,seed=20261030)
        return env,result

    def test_full_source_loop_and_authored_prompts_exact(self):
        env,result=self.run_policy('J')
        reference=original_reference(env.jev_schedule,env.jev_prompts)
        self.assertEqual(env.rows,reference);self.assertEqual(len(env.rows),1280)
        self.assertEqual(result['decisions'],320);self.assertEqual(env.match,64)
        self.assertEqual(len({tuple(r[1:3]) for r in env.rows}),64)

    def test_external_action_changes_opponent_history_and_payoff(self):
        cooperative,_=self.run_policy('J');defective,_=self.run_policy('F')
        # Match1 is act_gpt4 vs TFT. Round2 TFT mirrors prior Jev action.
        self.assertEqual(cooperative.rows[21][4],'J');self.assertEqual(defective.rows[21][4],'F')
        self.assertNotEqual(cooperative.rows[21][5:9],defective.rows[21][5:9])
        self.assertEqual(defective.rows,original_reference(defective.jev_schedule,defective.jev_prompts))

    def test_source_htft_quirk_and_atomic_invalid_actions(self):
        env=OriginalTournament();batch=env.prepare(1)
        self.assertEqual(env.ns['act_htft']('',1,'','',''),'F')
        with self.assertRaises(ValueError):env.advance(1,{q:'bad' for q in batch.questions},{})
        self.assertEqual(env.rows,[])

    def test_legacy_argmax_comparison(self):
        p=FunctionEngine(lambda s,q:{'J':.4,'F':.6});e=GreedyDecisionEngine(p)
        self.assertEqual(e.decide('',{'a':{}}),{'a':{'J':0.0,'F':1.0}})

    def test_default_sampling_retains_both_actions_and_feedback(self):
        env=OriginalTournament()
        probabilities=FunctionEngine(lambda s,q:{'J':.4,'F':.6})
        result=run_simulation(env,probabilities,rounds=300,seed=20261030)
        self.assertEqual(env.describe()['action_policy'],'sample')
        self.assertEqual(result['decisions'],320)
        self.assertIn('J',env.jev_schedule);self.assertIn('F',env.jev_schedule)
        self.assertEqual(env.rows,original_reference(env.jev_schedule,env.jev_prompts))


if __name__=='__main__':unittest.main()
