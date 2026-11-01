import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid
from orgabm.sdk import DecisionBatch, FunctionEngine, run_simulation
from orgabm.plans import expand_plan
from orgabm.deepseek import DeepSeekEngine


class TinyWorld:
    def __init__(self): self.commits=0
    def describe(self): return {'scenario':'test_custom_environment'}
    def prepare(self,t):
        return DecisionBatch('Local facts only.', {f'{t}-a': {'instructions':'Choose.',
                             'criteria':{'hold':'Wait','act':'Act'}}}, {f'{t}-a':'employee'})
    def advance(self,t,actions,probabilities):
        self.commits+=1
        return {'round':t,'action':next(iter(actions.values()))}


class Foundation(unittest.TestCase):
    def test_custom_environment_without_organization_code(self):
        world=TinyWorld()
        r=run_simulation(world,FunctionEngine(lambda s,q:{'hold':1,'act':0}),rounds=3,seed=2)
        self.assertEqual(world.commits,3)
        self.assertEqual(r['decisions'],3)

    def test_invalid_probabilities_do_not_commit(self):
        for p in [{'hold':1},{'hold':float('nan'),'act':0},{'hold':0.8,'act':0.8}]:
            world=TinyWorld()
            with self.assertRaises(ValueError):
                run_simulation(world,FunctionEngine(lambda s,q:p),rounds=1,seed=2)
            self.assertEqual(world.commits,0)

    def test_plan_grid_uses_paired_seeds(self):
        plan=expand_plan({'base':{'agents':16,'rounds':2},'vary':{'contact':['siloed','bridge']},'seeds':[3,4]})
        self.assertEqual(plan['worlds'],4)
        self.assertEqual(plan['decisions'],128)
        self.assertEqual([c['seed'] for c in plan['configs']],[3,4,3,4])
        with self.assertRaises(ValueError):expand_plan({'base':{'api_key':'not-a-credential'}})

    def test_jev_plan_counts_native_batches_and_excludes_chat_agents(self):
        plan=expand_plan({'base':{'agents':16,'rounds':3},'seeds':[7,8],
                          'decision':{'provider':'jev','batch_size':6,'concurrency':2}})
        self.assertEqual(plan['decisions'],96)
        self.assertEqual(plan['provider_requests'],18)
        self.assertTrue(all(c['engine']=='jev' and c['batch_size']==6 for c in plan['configs']))
        with self.assertRaises(ValueError):expand_plan({'decision':{'provider':'deepseek'}})
        with self.assertRaises(ValueError):expand_plan({'decision':{'provider':'jev','batch_size':0}})

    def test_deepseek_contract_and_round_request_cap(self):
        q={'id':{'instructions':'Local observation','criteria':{'hold':'Wait','act':'Act'}}}
        raw={'model':'test-model','choices':[{'finish_reason':'stop','message':{'content':'{"action":"act"}'}}],
             'usage':{'prompt_tokens':10,'completion_tokens':5}}
        with patch.dict(os.environ,{'DEEPSEEK_API_KEY':'test-only-placeholder'}):
            engine=DeepSeekEngine(max_requests=1,thinking=False)
            with patch.object(engine.opener,'open',return_value=io.BytesIO(json.dumps(raw).encode())) as call:
                self.assertEqual(engine.decide('state',q),{'id':{'hold':0.0,'act':1.0}})
                request=call.call_args.args[0]
                payload=json.loads(request.data)
                self.assertEqual(request.full_url,'https://api.deepseek.com/chat/completions')
                self.assertEqual(payload['response_format'],{'type':'json_object'})
                self.assertEqual(payload['thinking'],{'type':'disabled'})
                self.assertNotIn('test-only-placeholder',json.dumps(payload))
            with self.assertRaises(ValueError):engine.decide('state',q)
            self.assertEqual(engine.usage()['successful_requests'],1)

    def test_custom_gateway_is_explicit_and_does_not_change_model_identity(self):
        with patch.dict(os.environ,{'LOCAL_TEST_KEY':'test-only-placeholder'}):
            engine=DeepSeekEngine(base_url='https://gateway.example/v1/',api_key_env='LOCAL_TEST_KEY',model='deepseek-v4.1-flash')
            self.assertEqual(engine.endpoint,'https://gateway.example/v1/chat/completions')
            self.assertEqual(engine.model,'deepseek-v4.1-flash')
            for invalid in ['http://gateway.example','https://user:password@gateway.example','https://gateway.example?key=x']:
                with self.assertRaises(ValueError):DeepSeekEngine(base_url=invalid,api_key_env='LOCAL_TEST_KEY')


try:
    from orgabm.mesa_bridge import organization_adapter, organization_rule
    HAS_MESA=True
except ImportError:
    HAS_MESA=False


@unittest.skipUnless(HAS_MESA,'Install .[mesa] to verify Mesa integration')
class MesaIntegration(unittest.TestCase):
    def test_mesa_matches_reference_dynamics(self):
        from orgabm.experiment import run
        for contact in ['siloed','bridge']:
            c=dict(agents=16,rounds=3,seed=7,departments=4,contact=contact,approval_gain=10)
            adapter=organization_adapter(c)
            result=run_simulation(adapter,organization_rule(),rounds=3,seed=7)
            self.assertEqual(result['metrics'],run(c)['metrics'])
            self.assertEqual(len(adapter.model.agents),16)
            self.assertEqual(adapter.model.steps,3)
            self.assertEqual(len(adapter.model.datacollector.get_model_vars_dataframe()),3)

    def test_harness_service_runs_and_inspects(self):
        from orgabm.mcp_server import ExperimentService
        root=Path('runs')/('service-test-'+uuid.uuid4().hex)
        service=ExperimentService(root)
        job=service.start({'base':{'agents':16,'rounds':2},'seeds':[3]})
        service.jobs[job['id']].result(timeout=30)
        self.assertEqual(service.get(job['id'])['status'],'complete')
        self.assertEqual(service.inspect(job['id'],0,2,0)['id'],'t2_a0')
        self.assertEqual(service.get(job['id'],wait_seconds=1)['status'],'complete')
        with self.assertRaises(ValueError):service.get(job['id'],wait_seconds=99)
        with self.assertRaises(ValueError):service.get('../outside')
        with self.assertRaises(ValueError):service.start({'decision':{'provider':'deepseek'}})
        service.pool.shutdown()

    def test_jev_service_uses_batch_engine_and_process_cost_guard(self):
        from orgabm.mcp_server import ExperimentService
        created=[]
        class FakeJev:
            def __init__(self,output,cap_usd,batch_size,concurrency):
                self.cost=0
                self.output=output
                created.append(dict(cap=cap_usd,batch=batch_size,concurrency=concurrency))
            def decide(self,state,questions):
                self.cost+=0.01
                return {q:{a:float(i==0) for i,a in enumerate(v['criteria'])} for q,v in questions.items()}
            def usage(self):return {'recorded_input_cost_usd':self.cost}
        service=ExperimentService(Path('runs')/('jev-service-'+uuid.uuid4().hex),
                                  allow_paid=True,max_requests=8,max_cost_usd=0.10)
        plan={'base':{'agents':8,'rounds':2,'departments':2},'seeds':[7,8],
              'decision':{'provider':'jev','batch_size':4,'concurrency':2}}
        with patch.dict(os.environ,{'TYPESAFE_API_KEY':'test-only-placeholder'}),patch('orgabm.engines.JevEngine',FakeJev):
            job=service.start(plan)
            service.jobs[job['id']].result(timeout=30)
            self.assertEqual(service.get(job['id'])['status'],'complete')
            self.assertEqual(service.remaining_requests,0)
            self.assertAlmostEqual(service.remaining_cost_usd,0.06)
            self.assertAlmostEqual(created[1]['cap'],0.08)
            self.assertEqual(created[0]['batch'],4)
            with self.assertRaises(ValueError):service.start(plan)
        service.pool.shutdown()


if __name__=='__main__':unittest.main()
