import io
import json
import os
from pathlib import Path
import ssl
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from orgabm.openrouter_reliable import ReliableOpenRouterJevEngine
from orgabm.sdk import run_simulation
from orgabm.decision_journal import DecisionJournal,ResumeDecisionEngine
from examples.llm_abm_cookbook.environments import MajorityOpinion


def response(request,**kwargs):
    body=json.loads(request.data)
    return io.BytesIO(json.dumps(dict(model='typesafe/jev-1.14-20261014',usage={'input_tokens':10,'output_tokens':3,'cost':.000001},
        answers={qid:dict(probabilities={a:float(i==0) for i,a in enumerate(q['criteria'])}) for qid,q in body['questions'].items()})).encode())


class ReliableDecisions(unittest.TestCase):
    def setUp(self):
        Path('.buildtmp').mkdir(exist_ok=True); self.tmp=tempfile.TemporaryDirectory(dir='.buildtmp');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.env=patch.dict(os.environ,{'RETRY_TEST_KEY':'offline-placeholder'});self.env.start();self.addCleanup(self.env.stop)
        self.q={'q':dict(type='choice',instructions='Choose.',criteria={'Q':'Q','M':'M'})}
    def engine(self,**kwargs):
        return ReliableOpenRouterJevEngine(self.root/'calls',api_key_env='RETRY_TEST_KEY',backoff_base=0,jitter=0,**kwargs)
    def test_timeout_retries_same_batch_and_keeps_ambiguous_reserve(self):
        e=self.engine(); data=[]
        def fake(request,**kwargs):
            data.append(request.data)
            if len(data)==1:raise TimeoutError('test-only')
            return response(request)
        with patch.object(e.transport,'open',side_effect=fake),patch('orgabm.openrouter_reliable.time.sleep'):
            answer=e.decide('state',self.q)
        self.assertEqual(data[0],data[1]);self.assertEqual(answer['q'],{'Q':1,'M':0})
        self.assertEqual(e.usage()['attempted_requests'],2);self.assertEqual(e.usage()['retry_attempts'],1)
        self.assertGreater(e.usage()['outstanding_or_uncertain_cost_reserve_usd'],0)
    def test_retry_after_is_honored(self):
        e=self.engine(); count=0
        def fake(request,**kwargs):
            nonlocal count
            count+=1
            if count==1:raise urllib.error.HTTPError(request.full_url,429,'limited',{'Retry-After':'2'},io.BytesIO(b'{}'))
            return response(request)
        with patch.object(e.transport,'open',side_effect=fake),patch('orgabm.openrouter_reliable.time.sleep') as sleep:
            e.decide('state',self.q)
        self.assertGreaterEqual(sleep.call_args.args[0],2)
    def test_auth_credit_and_bad_request_are_terminal(self):
        for status in (400,401,402,403,404):
            with self.subTest(status=status):
                e=self.engine()
                with patch.object(e.transport,'open',side_effect=urllib.error.HTTPError('https://openrouter.ai',status,'terminal',{},io.BytesIO(b'{}'))) as request:
                    with self.assertRaises(RuntimeError):e.decide('state',self.q)
                    self.assertEqual(request.call_count,1)
    def test_in_flight_402_with_retry_after_is_transient(self):
        e=self.engine(); count=0
        def fake(request,**kwargs):
            nonlocal count
            count+=1
            if count==1:raise urllib.error.HTTPError(request.full_url,402,'budget',{'Retry-After':'1'},io.BytesIO(b'{"error":{"metadata":{"limit_source":"openrouter_in_flight_budget"}}}'))
            return response(request)
        with patch.object(e.transport,'open',side_effect=fake),patch('orgabm.openrouter_reliable.time.sleep'):
            e.decide('state',self.q)
        self.assertEqual(count,2)
    def test_certificate_and_invalid_response_are_not_retried(self):
        for error in (urllib.error.URLError(ssl.SSLCertVerificationError('test-only')),json.JSONDecodeError('bad','',0)):
            e=self.engine()
            with patch.object(e.transport,'open',side_effect=error) as request:
                with self.assertRaises(RuntimeError):e.decide('state',self.q)
                self.assertEqual(request.call_count,1)
    def test_exhaustion_does_not_advance_world(self):
        e=self.engine(max_retries=2);w=MajorityOpinion(agents=6)
        with patch.object(e.transport,'open',side_effect=TimeoutError('test-only')) as request,patch('orgabm.openrouter_reliable.time.sleep'):
            with self.assertRaises(RuntimeError):run_simulation(w,e,rounds=1,seed=3)
        self.assertEqual(request.call_count,3);self.assertEqual(w.round,0);self.assertTrue(e.failed)
    def test_retry_cannot_bypass_shared_request_limit(self):
        e=self.engine(max_requests=1)
        with patch.object(e.transport,'open',side_effect=TimeoutError('test-only')) as request,patch('orgabm.openrouter_reliable.time.sleep'):
            with self.assertRaises(Exception):e.decide('state',self.q)
        self.assertEqual(request.call_count,1)
    def test_invalid_probabilities_stop_without_retry_or_state_advance(self):
        e=self.engine();w=MajorityOpinion(agents=6)
        def invalid(request,**kwargs):
            body=json.loads(request.data)
            return io.BytesIO(json.dumps(dict(model='typesafe/jev-1.14-20261014',usage={'input_tokens':10,'output_tokens':3,'cost':.000001},
                answers={qid:dict(probabilities={a:.9 for a in q['criteria']}) for qid,q in body['questions'].items()})).encode())
        with patch.object(e.transport,'open',side_effect=invalid) as request:
            with self.assertRaises(Exception):run_simulation(w,e,rounds=1,seed=3)
        self.assertEqual(request.call_count,1);self.assertEqual(w.round,0)
    def test_recovery_usage_preserves_original_smaller_allowances(self):
        from examples.organizational_conventions.resume_reliable import combined_usage
        previous=dict(client_cap_usd=.1,client_max_requests=20,models_returned=['model'],attempted_requests=3,
            successful_responses=2,input_tokens=10,output_tokens=2,recorded_input_cost_usd=.01,retry_attempts=1)
        new=dict(models_returned=['model'],attempted_requests=2,successful_responses=2,input_tokens=10,
            output_tokens=2,recorded_input_cost_usd=.02)
        total=combined_usage(previous,new)
        self.assertEqual(total['client_cap_usd'],.1);self.assertEqual(total['client_max_requests'],20)
        self.assertEqual(total['attempted_requests'],5);self.assertEqual(total['unsuccessful_transport_attempts'],1)
    def test_exact_event_journal_only_recovers_matching_inputs(self):
        row=dict(request={'model':'typesafe/jev-1.14','state':'state','questions':self.q},response={
            'model':'typesafe/jev-1.14-20261014','answers':{'q':{'probabilities':{'Q':1,'M':0}}}})
        path=self.root/'journal.jsonl';path.write_text(json.dumps(row)+'\n',encoding='utf-8')
        journal=DecisionJournal([path]); e=self.engine()
        r=ResumeDecisionEngine(e,journal,io.StringIO(''),0)
        with patch.object(e.transport,'open',side_effect=response) as request:
            answer=r.decide('state',{**self.q,'new':self.q['q']})
            submitted=json.loads(request.call_args.args[0].data)['questions']
        self.assertEqual(set(submitted),{'new'});self.assertEqual(set(answer),{'q','new'})
        with self.assertRaises(ValueError):journal.recover('different state',self.q)
        log=(self.root/'calls'/'openrouter_calls.jsonl').read_text(encoding='utf-8')
        self.assertNotIn('offline-placeholder',log)


if __name__=='__main__':unittest.main()
