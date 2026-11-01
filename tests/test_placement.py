import copy
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

from orgabm.placement import preview_assignment, assign_personas, save_assignment
from orgabm.workforce import build_workforce
from orgabm.organization import memberships
from orgabm.experiment import run
from orgabm.sdk import FunctionEngine


def job(mode='stream', **options):
    records = [dict(id=f'p-{i}', description=f'Fictional candidate {i}',
                    background={'score_fixture': [.49, .5, .9, .1, .8, .7, .6, .2][i]},
                    source={'dataset':'synthetic test'}) for i in range(8)]
    return dict(config=dict(agents=4, departments=1, rounds=2, seed=7,
                           population={'records':records}, structure={'template':'flat'}),
                mode=mode, threshold=.5, seed=2, batch_size=2, **options)


def fixture_engine():
    return FunctionEngine(lambda state, q: {
        'holds_position': json.loads(q['instructions'])['persona']['background']['score_fixture'],
        'does_not_hold_position': 1-json.loads(q['instructions'])['persona']['background']['score_fixture']},
        name='synthetic-test-probabilities')


class PlacementTests(unittest.TestCase):
    def test_threshold_is_inclusive_not_bernoulli_or_top_k(self):
        spec=job()
        result=assign_personas(spec, fixture_engine())
        self.assertEqual(result['status'],'complete')
        self.assertEqual(result['assigned'],4)
        self.assertTrue(all(r['probability']>=.5 for r in result['assignments']))
        # Across seeds, the exactly-0.5 candidate can enter; a 0.49 candidate never does.
        selected=set()
        for seed in range(12):
            trial=assign_personas({**spec,'seed':seed}, fixture_engine())
            selected.update(r['persona_id'] for r in trial['assignments'])
        self.assertIn('p-1',selected)
        self.assertNotIn('p-0',selected)
        self.assertEqual(result,assign_personas(spec,fixture_engine()))
        self.assertEqual(spec,job())  # No changes to the source pool or request.

    def test_pool_scores_every_pair_and_samples_weights_not_top_k(self):
        selected=set()
        spec=job('pool')
        for seed in range(16):
            result=assign_personas({**spec,'seed':seed},fixture_engine())
            self.assertEqual(result['evaluated_pairs'],8)
            self.assertEqual(result['status'],'complete')
            selected.update(r['persona_id'] for r in result['assignments'])
        self.assertIn('p-0',selected)  # Pool mode has no stream threshold.
        self.assertIn('p-3',selected)  # Low weight still possible, not a rank cutoff.

    def test_incomplete_does_not_lower_threshold_duplicate_or_export_config(self):
        spec={**job(),'threshold':.85}
        result=assign_personas(spec,fixture_engine())
        self.assertEqual(result['status'],'incomplete')
        self.assertEqual(result['assigned'],1)
        self.assertEqual(result['missing_by_role'],{'employee':3})
        self.assertIsNone(result['config'])
        with tempfile.TemporaryDirectory() as directory:
            save_assignment(result,directory)
            self.assertTrue((Path(directory)/'assignment.json').exists())
            self.assertFalse((Path(directory)/'config.json').exists())
        capped=assign_personas({**job(),'max_evaluations':3},fixture_engine())
        self.assertEqual(capped['evaluated_pairs'],3)
        self.assertEqual(capped['stop_reason'],'evaluation_limit')

    def test_two_roles_freeze_layout_and_keep_scores_out_of_agent_observations(self):
        spec=json.loads(Path('examples/persona_assignment.json').read_text(encoding='utf-8'))
        def classify(state,q):
            data=json.loads(q['instructions'])
            self.assertNotIn('source',data['persona'])
            manager='manager' in data['position']['title'].lower()
            match=('manager' in data['persona']['background']['occupation'].lower()) == manager
            p=.9 if match else .1
            return {'holds_position':p,'does_not_hold_position':1-p}
        result=assign_personas(spec,FunctionEngine(classify))
        self.assertEqual(result['status'],'complete')
        self.assertEqual(len({a['persona_id'] for a in result['assignments']}),8)
        completed=result['config']
        self.assertEqual(completed['structure']['template'],'custom')
        first=build_workforce(completed,memberships(completed))
        another={**completed,'seed':77}
        self.assertEqual(first,build_workforce(another,memberships(another)))
        simulated=run(completed)
        self.assertEqual(simulated['decisions'],16 if completed['rounds']==2 else 24)
        for trace in simulated['traces']:
            self.assertNotIn('orgabm_assignment',json.dumps(trace['observation']))
        self.assertTrue(all(r['persona']['source']['orgabm_assignment']['probability']==.9 for r in first))

    def test_invalid_requests_and_model_responses(self):
        for update in [{'mode':'embedding'},{'threshold':float('nan')},{'threshold':True},
                       {'batch_size':0},{'max_evaluations':0},{'seed':-1}]:
            with self.subTest(update=update),self.assertRaises(ValueError):
                preview_assignment({**job(),**update})
        with self.assertRaises(ValueError):preview_assignment({**job('pool'),'max_evaluations':2})
        broken=job();broken['config']['population']['records']=broken['config']['population']['records'][:2]
        with self.assertRaises(ValueError):preview_assignment(broken)
        for values in [{'holds_position':.9}, {'holds_position':.8,'does_not_hold_position':.8},
                       {'holds_position':float('nan'),'does_not_hold_position':0}]:
            with self.subTest(values=values),self.assertRaises(ValueError):
                assign_personas(job(),FunctionEngine(lambda s,q:values))

    def test_no_candidate_role_pair_is_judged_twice_and_batch_tail_is_recorded(self):
        result=assign_personas({**job(),'batch_size':8},fixture_engine())
        ids=[row['question_id'] for row in result['evaluations']]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(result['evaluated_pairs'],8)
        self.assertTrue(any(row['outcome']=='unused_batch_tail' for row in result['evaluations']))

    def test_native_jev_batches_logs_usage_and_preview_bound(self):
        from orgabm.engines import JevEngine
        payloads=[]
        def http(request,timeout):
            payload=json.loads(request.data);payloads.append(payload)
            return io.BytesIO(json.dumps(dict(model='jev-1.14.0',usage={'input_tokens':10},answers={
                qid:{'probabilities':{'holds_position':.75,'does_not_hold_position':.25}}
                for qid in payload['questions']})).encode())
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'TYPESAFE_API_KEY':'test-placeholder'}):
            engine=JevEngine(directory,batch_size=2,concurrency=1)
            with patch('orgabm.engines.urllib.request.urlopen',side_effect=http):
                result=assign_personas(job(),engine,output=directory)
            save_assignment(result,directory)
            events=[json.loads(line) for line in (Path(directory)/'assignment-events.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(events[-1]['status'],'complete')
            self.assertTrue((Path(directory)/'config.json').exists())
        self.assertEqual(len(payloads),2)
        self.assertTrue(all(len(p['questions'])==2 for p in payloads))
        self.assertEqual(result['usage']['successful_requests'],2)
        self.assertLessEqual(len(payloads),preview_assignment(job())['max_provider_requests'])
        self.assertNotIn('quota',json.dumps(payloads[0]['questions']))

    def test_assignment_http_preview_is_free(self):
        from orgabm.server import Handler
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            req=Request(f'http://127.0.0.1:{server.server_port}/api/personas/assignment-preview',
                        data=json.dumps(job()).encode(),headers={'Content-Type':'application/json'})
            with urlopen(req,timeout=10) as response: result=json.load(response)
            self.assertEqual(result['threshold'],.5)
            self.assertEqual(result['roles']['employee']['count'],4)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)

    def test_mcp_assignment_uses_allowances_and_never_runs_abm(self):
        from orgabm.mcp_server import ExperimentService
        from orgabm.engines import JevEngine
        def http(request,timeout):
            payload=json.loads(request.data)
            return io.BytesIO(json.dumps(dict(model='jev-1.14.0',usage={'input_tokens':10},answers={
                q:{'probabilities':{'holds_position':1,'does_not_hold_position':0}} for q in payload['questions']})).encode())
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'TYPESAFE_API_KEY':'test-placeholder'}):
            service=ExperimentService(directory,allow_paid=False,max_requests=10)
            with self.assertRaises(ValueError):service.start_assignment(job())
            service.allow_paid=True
            with patch('orgabm.engines.urllib.request.urlopen',side_effect=http):
                started=service.start_assignment(job())
                result=service.get(started['id'],wait_seconds=15)
            service.pool.shutdown(wait=True)
            self.assertEqual(result['status'],'complete')
            self.assertEqual(result['kind'],'persona_assignment')
            self.assertEqual(service.remaining_requests,8)
            self.assertEqual(result['usage']['successful_requests'],2)
            self.assertTrue(Path(result['config_file']).exists())
            self.assertFalse(any((Path(directory)/started['id']).glob('world-*')))


if __name__=='__main__':unittest.main()
