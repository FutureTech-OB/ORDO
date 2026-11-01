import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from orgabm.openrouter import OpenRouterJevEngine
from orgabm.sdk import run_simulation
from examples.llm_abm_cookbook.environments import MajorityOpinion


def response_for(request):
    payload=json.loads(request.data)
    return dict(model='typesafe/jev-1.14-20261014',provider='TypeSafe',
        usage={'input_tokens':10,'output_tokens':5,'cost':0.000001},
        answers={qid:dict(type='choice',probabilities={k:float(i==0) for i,k in enumerate(q['criteria'])})
                 for qid,q in payload['questions'].items()})


class OpenRouterJev(unittest.TestCase):
    def setUp(self):
        Path('.buildtmp').mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir='.buildtmp'); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.env=patch.dict(os.environ,{'ORDO_TEST_KEY':'offline-placeholder'})
        self.env.start(); self.addCleanup(self.env.stop)

    def engine(self,**kwargs):
        return OpenRouterJevEngine(self.root/'calls',api_key_env='ORDO_TEST_KEY',**kwargs)

    def test_native_batching_dated_snapshot_and_provider_cost(self):
        engine=self.engine(batch_size=2,max_requests=2)
        questions={str(i):dict(type='choice',instructions='Choose.',criteria={'Q':'Q','M':'M'}) for i in range(3)}
        requests=[]
        def fake(request,**kwargs):
            requests.append(request)
            return io.BytesIO(json.dumps(response_for(request)).encode())
        with patch.object(engine.opener,'open',side_effect=fake):
            result=engine.decide('shared state',questions)
        self.assertEqual(set(result),set(questions))
        self.assertEqual([len(json.loads(r.data)['questions']) for r in requests],[2,1])
        self.assertTrue(all(r.full_url=='https://openrouter.ai/api/alpha/decisions' for r in requests))
        self.assertEqual(engine.usage()['recorded_input_cost_usd'],.000002)
        self.assertEqual(engine.usage()['input_tokens'],20)
        log=(self.root/'calls'/'openrouter_calls.jsonl').read_text(encoding='utf-8')
        self.assertNotIn('offline-placeholder',log)
        self.assertNotIn('Authorization',log)

    def test_wrong_model_stops_engine_before_another_submission(self):
        engine=self.engine(); world=MajorityOpinion(agents=6); q=world.prepare(1)
        def fake(request,**kwargs):
            raw=response_for(request); raw['model']='typesafe/jev-router'
            return io.BytesIO(json.dumps(raw).encode())
        with patch.object(engine.opener,'open',side_effect=fake) as transport:
            with self.assertRaisesRegex(ValueError,'model family'): engine.decide(q.state,q.questions)
            with self.assertRaises(RuntimeError): engine.decide(q.state,q.questions)
            self.assertEqual(transport.call_count,1)

    def test_missing_cost_is_not_silently_estimated(self):
        engine=self.engine(); q=MajorityOpinion(agents=6).prepare(1)
        def fake(request,**kwargs):
            raw=response_for(request); del raw['usage']['cost']
            return io.BytesIO(json.dumps(raw).encode())
        with patch.object(engine.opener,'open',side_effect=fake):
            with self.assertRaisesRegex(ValueError,'cost'): engine.decide(q.state,q.questions)
        self.assertTrue(engine.usage()['stopped_after_error'])

    def test_invalid_actions_do_not_advance_world(self):
        engine=self.engine(); world=MajorityOpinion(agents=6); before=copy.deepcopy(world.opinions)
        def fake(request,**kwargs):
            raw=response_for(request)
            for answer in raw['answers'].values(): answer['probabilities']={'unavailable':1}
            return io.BytesIO(json.dumps(raw).encode())
        with patch.object(engine.opener,'open',side_effect=fake):
            with self.assertRaises(ValueError): run_simulation(world,engine,rounds=1,seed=7)
        self.assertEqual(world.round,0); self.assertEqual(world.opinions,before)

    def test_request_allowance_and_question_type_are_checked(self):
        engine=self.engine(max_requests=1); q=MajorityOpinion(agents=6).prepare(1)
        with patch.object(engine.opener,'open',side_effect=lambda req,**kw:io.BytesIO(json.dumps(response_for(req)).encode())) as transport:
            engine.decide(q.state,q.questions)
            with self.assertRaises(ValueError): engine.decide(q.state,q.questions)
            self.assertEqual(transport.call_count,1)
        with self.assertRaises(ValueError): engine.decide('',{'q':dict(type='noul')})
        with self.assertRaises(ValueError): self.engine(model='typesafe/jev-router')
        with self.assertRaises(ValueError): self.engine(cap_usd=0)

    def test_allowance_can_prevent_first_submission(self):
        engine=self.engine(cap_usd=1e-12); q=MajorityOpinion(agents=6).prepare(1)
        with patch.object(engine.opener,'open') as transport:
            with self.assertRaises(ValueError): engine.decide(q.state,q.questions)
            transport.assert_not_called()


if __name__=='__main__': unittest.main()
