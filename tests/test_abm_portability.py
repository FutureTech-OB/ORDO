"""Behavioral portability: compare real upstream dynamics, not adapter internals."""
import copy
import unittest
from unittest.mock import patch

from examples.abm_cookbook.adapters import ExistingMesaEnvironment,direct_reference
from examples.abm_cookbook.run import preview,smoke_cases
from orgabm.sdk import FunctionEngine
from orgabm.staged import run_staged_simulation


class ABMPortabilityTests(unittest.TestCase):
    def check_native(self,kind,config):
        env=ExistingMesaEnvironment(kind,config)
        result=run_staged_simulation(env,env.native_engine(),rounds=config['rounds'],seed=config['seed'])
        native=direct_reference(kind,config)
        self.assertEqual(env.initial,native['initial'])
        self.assertEqual(env.trajectory,native['states'])
        self.assertEqual(result['metrics'],native['metrics'])

    def test_wealth_retains_async_transfers_rng_and_conservation(self):
        for seed in (7,8):
            self.check_native('wealth',dict(n=24,width=4,height=4,rounds=5,seed=seed))

    def test_schelling_retains_cached_happiness_and_shuffled_relocation(self):
        for threshold in (.3,.6):
            self.check_native('schelling',dict(width=8,height=8,density=.7,homophily=threshold,rounds=5,seed=7))

    def test_cooperation_preserves_all_three_activation_regimes(self):
        for mode in ('Simultaneous','Sequential','Random'):
            self.check_native('cooperation',dict(width=6,height=6,activation_order=mode,
                defection_bonus=1.8,rounds=5,seed=8))

    def test_replacement_engine_changes_decisions_inside_same_environment(self):
        c=dict(width=6,height=6,activation_order='Simultaneous',defection_bonus=1.6,rounds=3,seed=7)
        a=ExistingMesaEnvironment('cooperation',c); b=ExistingMesaEnvironment('cooperation',c)
        self.assertEqual(a.initial,b.initial)
        cooperate=FunctionEngine(lambda s,q:{'C':1.,'D':0.},name='always-cooperate')
        defect=FunctionEngine(lambda s,q:{'C':0.,'D':1.},name='always-defect')
        ra=run_staged_simulation(a,cooperate,rounds=3,seed=7)
        rb=run_staged_simulation(b,defect,rounds=3,seed=7)
        self.assertEqual(ra['metrics'][-1]['cooperation_share'],1)
        self.assertEqual(rb['metrics'][-1]['cooperation_share'],0)
        self.assertNotEqual(a.trajectory,b.trajectory)

    def test_jev_serializes_actual_adapter_questions_and_uses_native_batches(self):
        import io,json,os,tempfile
        from orgabm.engines import JevEngine
        c=dict(width=4,height=4,activation_order='Simultaneous',defection_bonus=1.6,rounds=1,seed=7)
        env=ExistingMesaEnvironment('cooperation',c); submitted=[]
        def response(request,timeout):
            payload=json.loads(request.data); submitted.append(payload)
            answers={qid:dict(probabilities={a:float(a=='C') for a in q['criteria']}) for qid,q in payload['questions'].items()}
            return io.BytesIO(json.dumps(dict(model=payload['model'],answers=answers,usage={'input_tokens':100})).encode())
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'TYPESAFE_API_KEY':'fixture-only-placeholder'}):
            engine=JevEngine(folder,batch_size=6,concurrency=1)
            with patch('orgabm.engines.urllib.request.urlopen',side_effect=response):
                result=run_staged_simulation(env,engine,rounds=1,seed=7)
        self.assertEqual([len(p['questions']) for p in submitted],[6,6,4])
        self.assertEqual(result['metrics'][0]['cooperation_share'],1)
        self.assertTrue(all('candidate_models' in q['instructions'] for p in submitted for q in p['questions'].values()))
        # Exercise the other two adapters through the same real HTTP serializer.
        def legal_response(request,timeout):
            payload=json.loads(request.data); submitted.append(payload)
            answers={qid:dict(probabilities={a:float(i==0) for i,a in enumerate(q['criteria'])})
                     for qid,q in payload['questions'].items()}
            return io.BytesIO(json.dumps(dict(model=payload['model'],answers=answers,usage={'input_tokens':100})).encode())
        for kind,config in [('wealth',dict(n=12,width=3,height=3,rounds=2,seed=7)),
                            ('schelling',dict(width=6,height=6,density=.7,homophily=.4,rounds=2,seed=7))]:
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'TYPESAFE_API_KEY':'fixture-only-placeholder'}):
                env=ExistingMesaEnvironment(kind,config)
                engine=JevEngine(folder,batch_size=6,concurrency=1)
                with patch('orgabm.engines.urllib.request.urlopen',side_effect=legal_response):
                    result=run_staged_simulation(env,engine,rounds=2,seed=7)
                self.assertEqual(result['status'],'complete')
                self.assertGreater(result['usage']['successful_requests'],0)

    def test_preview_has_no_inference_and_distinguishes_dependent_stages(self):
        specs=smoke_cases()
        with patch('orgabm.engines.JevEngine.decide',side_effect=AssertionError('No preview inference')):
            p=preview(specs,batch_size=64)
        self.assertEqual(p['cases'][0]['requests_upper_bound'],24)
        self.assertEqual(p['cases'][2]['requests_upper_bound'],3)
        altered=copy.deepcopy(specs[2]); altered['config']['activation_order']='Random'
        self.assertEqual(preview([altered])['requests_upper_bound'],108)

    def test_cannot_reorder_stages_or_advance_before_choices(self):
        e=ExistingMesaEnvironment('wealth',dict(n=8,width=3,height=3,rounds=2,seed=7))
        stages=e.stages(1)
        with self.assertRaises(ValueError): e.prepare_stage(1,stages[1])
        with self.assertRaises(ValueError): e.finish_round(1)
        self.assertEqual(e.model.steps,0)


if __name__=='__main__': unittest.main()
