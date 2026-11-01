import copy
import io
import json
from pathlib import Path
import pickle
import tempfile
import unittest

from orgabm.sdk import FunctionEngine, run_simulation
from examples.llm_abm_cookbook.environments import NamingGame, MajorityOpinion, recover_initial_agents
from examples.llm_abm_cookbook.run import replay_naming
from examples.llm_abm_cookbook.sources import DataOnlyUnpickler, split_opinion_trace, numeric_rows
from examples.llm_abm_cookbook.verify_interfaces import verify_interfaces


def explicit_fixture():
    # Hand-calculated, fictional fixture; not presented as published model output.
    return dict(simulation={
        1:dict(my_history=['Q','Q','M'],partner_history=['M','Q','M'],interactions=[2,2,2],
               score_history=[-50,50,150],outcome=[-50,100,100],score=150,committed_tag=False,neighbours=[2]),
        2:dict(my_history=['M','Q','M'],partner_history=['Q','Q','M'],interactions=[1,1,1],
               score_history=[-50,50,150],outcome=[-50,100,100],score=150,committed_tag=False,neighbours=[1])},
        tracker=dict(players=[[1,2],[2,1],[1,2]],answers=[['Q','M'],['Q','Q'],['M','M']],outcome=[0,1,1]),
        convergence={'converged_index':None,'committed_to':None})


class LLMCookbook(unittest.TestCase):
    def setUp(self):
        Path('.buildtmp').mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir='.buildtmp')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def test_explicit_archive_fixture_matches_all_histories_and_payoffs(self):
        report=replay_naming(explicit_fixture(),self.root/'replay',['Q','M'])
        self.assertEqual(report['interactions'],3)
        self.assertEqual(report['decisions'],6)
        self.assertTrue(report['source_final_individual_state_exact'])
        log=json.loads((self.root/'replay'/'result.json').read_text(encoding='utf-8'))
        self.assertEqual(log['usage']['probability_semantics'],'one_hot_recorded_sample_not_model_probabilities')

    def test_corrupted_source_outcome_is_detected(self):
        data=explicit_fixture(); data['tracker']['outcome'][0]=1
        with self.assertRaisesRegex(AssertionError,'tracker'):
            replay_naming(data,self.root/'bad',['Q','M'])

    def test_prefilled_memory_has_no_invented_partner_ids(self):
        data=explicit_fixture()
        for row in data['simulation'].values():
            for key in ('my_history','partner_history'): row[key]=['Q']*5+row[key]
            row['outcome']=[100]*5+row['outcome']
            row['score_history']=[100,200,300,400,500]+[x+500 for x in row['score_history']]
            row['score']+=500
        initial=recover_initial_agents(data)
        self.assertEqual(initial[1]['my_history'],['Q']*5)
        self.assertEqual(initial[1]['interactions'],[])
        self.assertEqual(initial[1]['score'],500)
        self.assertTrue(replay_naming(data,self.root/'prefilled',['Q','M'])['source_final_individual_state_exact'])

    def test_pair_is_prepared_simultaneously_and_history_is_private_window(self):
        world=NamingGame(agents=2,memory_size=5)
        run_simulation(world,FunctionEngine(lambda s,q:{'Q':1,'M':0}),rounds=6,seed=7)
        self.assertEqual(world.agents[1]['score'],600)
        before=copy.deepcopy(world.agents)
        batch=world.prepare(7)
        self.assertEqual(len(batch.questions),2)
        self.assertEqual(world.agents[1]['my_history'],['Q']*6)
        self.assertEqual(world.local_view(1)['local_score'],500)
        self.assertEqual([r['round'] for r in world.local_view(1)['history']],[1,2,3,4,5])
        self.assertNotIn('600',json.dumps(batch.questions))
        self.assertEqual(world.agents,before)
        world.advance(7,{qid:'Q' if a==1 else 'M' for qid,a in batch.agent_ids.items()}, {})
        self.assertEqual([world.agents[a]['score'] for a in [1,2]],[550,550])

    def test_committed_agent_is_fixed_without_an_engine_question(self):
        world=NamingGame(agents=2)
        world.agents[2]['committed_tag']=True; world.committed_to='M'
        batch=world.prepare(1)
        self.assertEqual(list(batch.agent_ids.values()),[1])
        world.advance(1,{next(iter(batch.questions)):'Q'}, {})
        self.assertEqual(world.agents[2]['my_history'],['M'])
        self.assertEqual(world.agents[1]['score'],-50)

    def test_majority_excludes_own_opinion_and_decodes_random_labels(self):
        world=MajorityOpinion(agents=6)
        before=list(world.opinions); batch=world.prepare(1)
        _,selected,mapping,peers=world.prepared
        self.assertEqual(len(batch.questions),1); self.assertEqual(len(peers),5)
        for value,label in mapping.items():
            self.assertEqual(sum(p['opinion']==label for p in peers),before.count(value)-int(before[selected]==value))
        qid=next(iter(batch.questions))
        result=world.advance(1,{qid:mapping[-before[selected]]},{})
        self.assertEqual(result['population_time'],1/6)
        self.assertAlmostEqual(abs(result['mean_opinion']),2/6)
        self.assertEqual(sum(a!=b for a,b in zip(world.opinions,before)),1)

    def test_appended_macro_trials_are_split_and_impossible_changes_rejected(self):
        segments=split_opinion_trace(b'0,0\n1,0.04\n0,0\n1,-0.04\n')
        self.assertEqual([len(s) for s in segments],[2,2])
        for raw in [b'0,0\n1,0.08\n',b'0,0.01\n',b'0,0\n2,0.04\n']:
            with self.assertRaises(ValueError): split_opinion_trace(raw)
        self.assertEqual(numeric_rows(b'0,98,100,0.49\n',columns=(2,4)),[[0,98,100,.49]])

    def test_pickle_global_construction_is_disabled(self):
        with self.assertRaises(pickle.UnpicklingError):
            DataOnlyUnpickler(io.BytesIO(pickle.dumps(Path('not-executed')))).load()
        self.assertEqual(DataOnlyUnpickler(io.BytesIO(pickle.dumps({'safe':[1,2]}))).load(),{'safe':[1,2]})

    def test_actual_engine_serializers_only_use_local_mock_transport(self):
        report=verify_interfaces(self.root/'interfaces')
        self.assertEqual(report['actual_network_requests'],0)
        self.assertEqual(len(report['cases']),4)
        self.assertEqual(sum(r['decisions'] for r in report['cases']),24)
        naming=next(r for r in report['cases'] if r['provider']=='jev' and r['scene']=='naming')
        self.assertEqual(naming['questions_per_mock_request'],[2]*4)
        opinion=next(r for r in report['cases'] if r['provider']=='jev' and r['scene']=='opinion')
        self.assertEqual(opinion['questions_per_mock_request'],[1]*4)


if __name__=='__main__': unittest.main()
