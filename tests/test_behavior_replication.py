import unittest

from orgabm.sdk import FunctionEngine,run_simulation
from examples.llm_abm_cookbook.behavior import PaperNamingGame,IndependentWorlds,make_naming_worlds,make_opinion_worlds


class BehavioralReplication(unittest.TestCase):
    def test_fresh_minority_initialization_and_local_context(self):
        world=PaperNamingGame(seed=3,initial='Q',target='M',committed=5)
        self.assertEqual(sum(r['committed_tag'] for r in world.agents.values()),5)
        self.assertTrue(all(r['my_history']==['Q']*5 and r['score']==500 for r in world.agents.values()))
        batch=world.prepare(1)
        self.assertTrue(all(not world.agents[a]['committed_tag'] for a in batch.agent_ids.values()))
        self.assertTrue(all('100 rounds' in q['instructions'] for q in batch.questions.values()))
        self.assertTrue(all('population' not in q['instructions'] and 'committed' not in q['instructions'] for q in batch.questions.values()))

    def test_independent_world_ids_and_update_barriers(self):
        worlds={w:PaperNamingGame(seed=i) for i,w in enumerate(['a','b'])}
        env=IndependentWorlds(worlds,{w:{} for w in worlds},max_updates={'a':2,'b':2})
        class Recorded:
            def __init__(self): self.calls=0
            def decide(self,state,questions):
                self.calls+=1
                assert all(w.round==self.calls-1 for w in worlds.values())
                assert len(questions)==4
                return {qid:{k:float(k=='M') for k in q['criteria']} for qid,q in questions.items()}
            def usage(self): return {}
        engine=Recorded(); result=run_simulation(env,engine,rounds=2,seed=7)
        self.assertEqual(result['decisions'],8)
        self.assertEqual([w.round for w in worlds.values()],[2,2])
        self.assertTrue(all(r['stop']=='horizon' for r in env.summaries()))

    def test_spontaneous_stops_but_old_minority_convention_does_not(self):
        world=PaperNamingGame(seed=3)
        env=IndependentWorlds({'a':world},{'a':{}},max_updates={'a':100})
        result=run_simulation(env,FunctionEngine(lambda s,q:{'Q':1,'M':0}),rounds=100,seed=7)
        self.assertEqual(world.round,72); self.assertEqual(result['decisions'],144)
        old=PaperNamingGame(seed=3,initial='Q',target='M',committed=0)
        control=IndependentWorlds({'a':old},{'a':{}},max_updates={'a':100})
        run_simulation(control,FunctionEngine(lambda s,q:{'Q':1,'M':0}),rounds=100,seed=7)
        self.assertEqual(old.round,100); self.assertNotIn('a',control.first_target_window)

    def test_minority_first_target_window_is_not_a_stop_rule(self):
        world=PaperNamingGame(seed=3,initial='Q',target='M',committed=4)
        env=IndependentWorlds({'a':world},{'a':{}},max_updates={'a':100})
        run_simulation(env,FunctionEngine(lambda s,q:{'Q':0,'M':1}),rounds=100,seed=7)
        self.assertEqual(world.round,100); self.assertEqual(env.first_target_window['a'],72)
        self.assertEqual(env.summaries()[0]['last']['mutable_target_share'],1)

    def test_declared_grid_is_unchanged_by_provider_results(self):
        naming=make_naming_worlds(); opinion=make_opinion_worlds()
        self.assertEqual(len(naming.worlds),20); self.assertEqual(len(opinion.worlds),16)
        self.assertEqual(sum(c['condition']=='N50' for c in opinion.configurations.values()),10)
        self.assertTrue(all(v==1000 for v in naming.max_updates.values()))
        self.assertTrue(all(opinion.max_updates[k]==10*w.n for k,w in opinion.worlds.items()))


if __name__=='__main__': unittest.main()
