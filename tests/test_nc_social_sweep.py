"""Checks on an author's RFIM fixture, stage barriers and irreversible activation."""
import json
from types import SimpleNamespace
import unittest
import numpy as np
from examples.nc_social_sweep.model import SocialActivation,native_engine
from orgabm.sdk import FunctionEngine,run_simulation
from examples.nc_social_sweep.foraging import ForagingEnvironment,AuthorPolicyEngine


class SocialPropagationTests(unittest.TestCase):
    def test_matches_recorded_author_c_kernel_shells(self):
        w=SocialActivation(agents=4,fields=[-.3,.1,.4,-.7])
        result=run_simulation(w,native_engine(),rounds=8,seed=7)
        self.assertEqual([x['shell_size'] for x in w.events],[1,1,1,1,0])
        self.assertEqual([x['remaining'] for x in w.events],[3,2,1,0,0])
        self.assertEqual([x['field'] for x in w.events],[.600001]*5)
        self.assertEqual(w.sizes,[4]);self.assertEqual(result['decisions'],4)

    def test_next_shell_observes_only_committed_preceding_activation(self):
        w=SocialActivation(agents=4,fields=[-.3,.1,.4,-.7])
        batch=w.prepare(1);self.assertEqual(len(batch.questions),1)
        q=next(iter(batch.questions));record=json.loads(batch.questions[q]['instructions'])
        self.assertEqual(record['collective_field'],-1)
        self.assertNotIn('all_fields',record);self.assertEqual(sum(w.active),0)
        w.advance(1,{q:'activate'},{q:{'activate':1,'defer':0}})
        following=w.prepare(2);self.assertEqual(len(following.questions),1)
        self.assertEqual(json.loads(next(iter(following.questions.values()))['instructions'])['collective_field'],-.5)

    def test_all_members_activate_once_and_padding_adds_no_decisions(self):
        for seed in (7,11,19):
            w=SocialActivation(agents=20,disorder=1.5,seed=seed)
            result=run_simulation(w,native_engine(),rounds=40,seed=seed)
            self.assertTrue(all(w.active));self.assertTrue(all(x is not None for x in w.activation_time))
            self.assertEqual(sum(w.sizes),20);self.assertEqual(result['decisions'],20)
            self.assertLessEqual(len(w.events),40)

    def test_invalid_probability_does_not_activate_any_member(self):
        w=SocialActivation(agents=4,fields=[-.3,.1,.4,-.7])
        bad=FunctionEngine(lambda state,q:{'activate':1.,'defer':1.})
        with self.assertRaises(ValueError):run_simulation(w,bad,rounds=8,seed=7)
        self.assertEqual(w.round,0);self.assertFalse(any(w.active))

    def test_foraging_question_contains_observed_rewards_only(self):
        view=SimpleNamespace(agent_rewards_map=np.array([[np.nan,1],[0,np.nan]]),
            agent_locs=np.array([[0,np.nan],[0,np.nan]]),agent_dirs=np.array([[0,np.nan],[1,np.nan]]),rewarded_agents=np.array([False,False]))
        world=SimpleNamespace(revealed_map=np.array([[False,True],[False,False]]),rewards_map=np.full((2,2),42))
        env=object.__new__(ForagingEnvironment);env.pending=None;env.final_result=None;env.round=0
        env.config={'policy':'asocial'};env.current=(0,0,view,world,None,None)
        batch=env.prepare(1);record=json.loads(next(iter(batch.questions.values()))['instructions'])
        self.assertEqual(len(record['observed_rewards']),2)
        self.assertEqual({x['reward'] for x in record['observed_rewards']},{0,1})
        self.assertNotIn('rewards_map',record);self.assertNotIn('42',json.dumps(record))
        json.dumps(record,allow_nan=False)

    def test_foraging_native_padding_does_not_draw_again(self):
        calls=[]
        class Policy:
            def sample_next_cell(self,view,state,rng):calls.append((view,state,rng));return 1,0
        env=SimpleNamespace(current=(0,0,'local-view','state',Policy(),'author-rng'))
        engine=AuthorPolicyEngine(env)
        self.assertEqual(engine.decide('complete',{}),{});self.assertFalse(calls)
        result=engine.decide('state',{'q':{'criteria':{'cell_0_0':'A','cell_1_0':'B'}}})
        self.assertEqual(result,{'q':{'cell_0_0':0.,'cell_1_0':1.}});self.assertEqual(len(calls),1)


if __name__=='__main__':unittest.main()
