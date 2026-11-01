import copy
import json
import unittest
import numpy as np

from examples.nc_evolutionary_games.model import RepeatedGame,AuthorStrategyEngine,direct_reference,digest,NAMES,source_manifest
from examples.nc_evolutionary_games.evolution import WellMixedEvolution,NativeImitation,evolution_reference
from orgabm.sdk import run_simulation
from orgabm.staged import run_staged_simulation


class NCEvolutionaryGames(unittest.TestCase):
    def test_pinned_authors_figure1_recovery_and_alternation_patterns(self):
        expected={
            (-1,(0,1)):[[0,1],[0,0],[0,0],[0,0]],
            (0,(0,1)):[[0,1],[1,0],[0,1],[1,0]],
            (6,(0,1)):[[0,1],[1,0],[0,1],[0,0]],
            (-1,(1,1)):[[1,1],[1,1],[0,0],[0,0]],
            (0,(1,1)):[[1,1],[1,1],[1,1],[1,1]],
            (6,(1,1)):[[1,1],[1,1],[0,0],[0,0]],
        }
        for (s,start),actions in expected.items():
            with self.subTest(strategy=s,start=start):
                w=RepeatedGame([s,s],start,20,7);r=run_simulation(w,AuthorStrategyEngine(w),rounds=20,seed=7)
                self.assertEqual(w.actions[:4],actions)
                self.assertEqual([m['state_sha256'] for m in r['metrics']],
                                 [digest(x) for x in direct_reference([s,s],start,20,7)])
        self.assertEqual(len(source_manifest()),3)
    def test_stochastic_and_stateful_author_strategies_match_original_loop(self):
        for a,b in [(-1,5),(-1,1),(6,5),(3,4),(1,15),(5,6)]:
            for seed in (7,11):
                w=RepeatedGame([a,b],[0,1],40,seed);r=run_simulation(w,AuthorStrategyEngine(w),rounds=40,seed=seed)
                self.assertEqual([m['state_sha256'] for m in r['metrics']],
                                 [digest(x) for x in direct_reference([a,b],[0,1],40,seed)])
    def test_questions_contain_only_own_game_history(self):
        w=RepeatedGame([-1,0],[0,1],20,7)
        batch=w.prepare(1)
        q=json.loads(batch.questions['t1_a0']['instructions'])
        self.assertEqual(q['player'],0);self.assertEqual(q['history'],[])
        self.assertNotIn('opponent_history',q);self.assertNotIn('Q',q)
        class Bad:
            def decide(self,state,questions):return {k:{'C':.9,'D':.9} for k in questions}
            def usage(self):return {}
        with self.assertRaises(ValueError):run_simulation(w,Bad(),rounds=1,seed=7)
        self.assertEqual(w.round,0);self.assertEqual(w.histories,[[],[]])
    def test_sequential_fermi_population_matches_extracted_author_generation(self):
        payoffs=[[3,0,2.5],[5,1,1.5],[2.5,1.5,2.0]];coop=[[1,1,.5],[0,0,.2],[.5,.2,.5]]
        for seed in (7,8):
            w=WellMixedEvolution(payoffs,coop,[-1,0,15],agents=12,rounds=10,selection=1,seed=seed)
            ref=evolution_reference(w)
            result=run_staged_simulation(w,NativeImitation(w),rounds=10,seed=seed)
            self.assertEqual([m['state_sha256'] for m in result['metrics']],[digest(r['types']) for r in ref])
            for m,r in zip(result['metrics'],ref):
                self.assertAlmostEqual(m['mean_payoff'],sum(r['fitness'])/12,places=12)
                self.assertEqual(sum(m['counts'].values()),12)


if __name__=='__main__':unittest.main()
