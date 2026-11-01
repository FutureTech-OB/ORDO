import copy
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer

from orgabm.personas import (import_personas, parse_personas, load_personas,
                            build_population, validate_population)
from orgabm.workforce import build_workforce, allowed_actions
from orgabm.organization import validate_config, memberships, contact_sets
from orgabm.experiment import run
from orgabm.plans import expand_plan
from orgabm.sdk import run_simulation


def config(**overrides):
    records = [dict(id=f'p-{i}', name=f'Person-{i}',
                    background={'experience': i}, traits={'private_marker': f'private-{i}'},
                    source={'dataset': 'fictional-test', 'revision': 'v1'}) for i in range(8)]
    return dict(agents=8, departments=2, rounds=2, seed=7,
                population={'records': records, 'sampling': 'ordered', 'seed': 11},
                structure={'template': 'department_hierarchy'}, **overrides)


class PersonaTests(unittest.TestCase):
    def test_public_dataset_adapters_preserve_fields_and_provenance(self):
        # Synthetic fixtures use the published schemas, not downloaded population data.
        n = import_personas([{'uuid': 'n-1', 'professional_persona': 'Test engineer',
            'persona': 'Methodical', 'age': 40, 'occupation': 'engineer',
            'skills_and_expertise': 'Testing', 'career_goals_and_ambitions': 'Improve quality'}],
            preset='nemotron', source={'revision': 'fixture-v1'})[0]
        self.assertEqual(n['background']['age'], 40)
        self.assertEqual(n['skills']['description'], 'Testing')
        self.assertEqual(n['goals'], ['Improve quality'])
        self.assertEqual(n['source']['license'], 'CC-BY-4.0')
        self.assertEqual(n['source']['revision'], 'fixture-v1')
        for preset in ['personahub', 'finepersonas']:
            p = import_personas([{'id': 12, 'persona': 'A fictional analyst', 'labels': ['analyst']}], preset=preset)[0]
            self.assertEqual(p['id'], '12')
            self.assertEqual(p['description'], 'A fictional analyst')
            self.assertTrue(p['source']['license'])

    def test_csv_jsonl_and_custom_columns(self):
        mapping = {'id': 'person_id', 'description': 'bio', 'background.occupation': 'job'}
        csv_data = 'person_id,bio,job\n1,"Studies, then tests",engineer\n'
        records = parse_personas(csv_data, format='csv', field_map=mapping)
        self.assertEqual(records[0]['background']['occupation'], 'engineer')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'people.jsonl'
            path.write_text('\n'.join(json.dumps(r) for r in records), encoding='utf-8')
            self.assertEqual(load_personas(path), records)
        nested = parse_personas('id,traits\nx,"{""risk"":0.2}"\n', format='csv')
        self.assertEqual(nested[0]['traits']['risk'], 0.2)

    def test_reject_bad_imports_and_sampling(self):
        invalid = [[], [{'id': 'x'}], [{'id': 'x', 'traits': {'risk': float('nan')}}],
                   [{'id': 'x', 'description': 'ok', 'manager': 2}],
                   [{'id': 'x', 'description': 'a'}, {'id': 'x', 'description': 'b'}]]
        for rows in invalid:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                import_personas(rows)
        with self.assertRaises(ValueError):
            import_personas([{'bio': 'x'}], field_map={'description': 'missing'})
        pool = config()['population']
        for update in [{'sampling': 'unknown'}, {'weights': [1]*8}, {'sampling': 'ordered', 'seed': True}]:
            with self.subTest(update=update), self.assertRaises(ValueError):
                validate_population({**pool, **update}, 8)
        with self.assertRaises(ValueError):
            validate_population({**pool, 'sampling': 'without_replacement'}, 9)

    def test_sampling_preserves_person_attributes_and_independent_state(self):
        raw = config()
        raw['population'].update(sampling='with_replacement', weights=[1]+[0]*7)
        c = validate_config(raw)
        people = build_population(c)
        self.assertEqual({p['id'] for p in people}, {'p-0'})
        people[0]['traits']['private_marker'] = 'modified'
        self.assertEqual(people[1]['traits']['private_marker'], 'private-0')
        self.assertEqual(c['population']['records'][0]['traits']['private_marker'], 'private-0')

    def test_same_people_across_structure_policy_and_world_seeds(self):
        raw = config()
        raw['population']['sampling'] = 'without_replacement'
        plan = expand_plan({'base': {k:v for k,v in raw.items() if k != 'seed'},
            'vary': {'structure': [{'template': 'flat'}, {'template': 'department_hierarchy'}],
                     'penalty': [0, 10]}, 'seeds': [7, 8]})
        populations = [build_population(c) for c in plan['configs']]
        self.assertTrue(all(p == populations[0] for p in populations))
        self.assertEqual(len({p['id'] for p in populations[0]}), 8)

    def test_persona_is_private_and_anonymous_hides_relationships(self):
        result = run(config())
        record = result['traces'][0]['observation']
        self.assertEqual(record['persona']['traits']['private_marker'], 'private-0')
        for i in range(1, 8):
            self.assertNotIn(f'private-{i}', json.dumps(record))
        self.assertNotIn('source', record['persona'])
        self.assertTrue(all('persona' not in p for p in record['coworkers']))
        hidden = run(config(anonymous=True))['traces'][0]['observation']
        self.assertIsNone(hidden['department'])
        self.assertNotIn('reports_to', hidden['organization'])
        self.assertNotIn('direct_reports', hidden['organization'])
        self.assertTrue(all(set(p) == {'slot','process','performance'} for p in hidden['coworkers']))

    def test_custom_structure_drives_contacts_and_rejects_cycles(self):
        raw = config()
        assignments = [dict(agent=a, department=a//4, role='employee', manager=None if a%4 == 0 else (a//4)*4) for a in range(8)]
        raw['structure'] = {'template':'custom', 'assignments':assignments}
        raw['contact'] = 'siloed'
        c = validate_config(raw)
        self.assertEqual(memberships(c), [0]*4+[1]*4)
        for a, peers in enumerate(contact_sets(c,memberships(c),1)):
            self.assertTrue(all(a//4 == b//4 for b in peers))
        for modification in ['cycle', 'duplicate', 'role', 'understaffed']:
            broken = copy.deepcopy(raw)
            rows = broken['structure']['assignments']
            if modification == 'cycle': rows[0]['manager'] = 1
            elif modification == 'duplicate': rows[0]['agent'] = 1
            elif modification == 'role': rows[0]['role'] = 'undefined'
            else: rows[0]['department'] = 1
            with self.subTest(modification=modification), self.assertRaises(ValueError):
                validate_config(broken)

    def test_role_permissions_change_action_space_and_enactment(self):
        raw = config()
        raw['structure']['roles'] = {
            'employee': {'allowed_actions':['keep']},
            'manager': {'allowed_actions':['keep','explore']}}
        result = run(raw)
        for row in result['workforce']:
            a = row['agent']
            if row['role'] == 'employee':
                self.assertEqual(result['final_positions'][a], run({**raw,'rounds':1})['final_positions'][a])
        for trace in result['traces']:
            permitted = trace['observation']['organization']['allowed_actions']
            self.assertEqual(set(trace['probabilities']), set(permitted))
            self.assertIn(trace['requested_action'], permitted)
        # Even a misbehaving direct engine cannot enact an unauthorized action.
        class InvalidEngine:
            def decide(self, state, questions): return {q:{'explore':1} for q in questions}
            def usage(self): return {'test_only':True}
        blocked = run({**raw, 'engine':'jev'}, InvalidEngine())
        self.assertEqual(blocked['metrics'][0]['role_permission_denials'],6)
        self.assertEqual(blocked['metrics'][0]['approval_denials'],0)

    def test_rules_ignore_descriptive_persona_and_hashes_record_changes(self):
        raw = config()
        first = run(raw)
        raw['population']['records'][0]['traits']['risk'] = 'different'
        second = run(raw)
        self.assertEqual(first['metrics'], second['metrics'])
        self.assertNotEqual(first['population_sha256'], second['population_sha256'])
        self.assertEqual(first['organization_sha256'], second['organization_sha256'])


try:
    from orgabm.mesa_bridge import organization_adapter, organization_rule
    HAS_MESA = True
except ImportError:
    HAS_MESA = False


@unittest.skipUnless(HAS_MESA, 'Install .[mesa]')
class PersonaMesaTests(unittest.TestCase):
    def test_mesa_matches_reference_and_persists_full_roster(self):
        raw = config()
        reference = run(raw)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'run'
            adapter = organization_adapter(raw)
            result = run_simulation(adapter,organization_rule(),rounds=2,seed=7,output=output)
            self.assertEqual(result['metrics'],reference['metrics'])
            self.assertEqual(result['environment']['population_sha256'],reference['population_sha256'])
            self.assertEqual(result['environment']['workforce'],reference['workforce'])
            events = [json.loads(line) for line in (output/'events.jsonl').read_text(encoding='utf-8').splitlines()]
            record = json.loads(events[0]['questions']['t1_a0']['instructions'].split('\n')[0])
            self.assertEqual(record['persona']['name'], 'Person-0')
            self.assertEqual(len(adapter.model.agents),8)

    def test_persona_reaches_native_jev_batches_every_round(self):
        from orgabm.engines import JevEngine
        payloads = []
        def fake_http(request, timeout):
            payload = json.loads(request.data)
            payloads.append(payload)
            return io.BytesIO(json.dumps({'model':'jev-1.14.0','usage':{'input_tokens':10},
                'answers':{q:{'probabilities':{a:float(a=='keep') for a in value['criteria']}}
                           for q,value in payload['questions'].items()}}).encode())
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'TYPESAFE_API_KEY':'test-placeholder'}):
            engine = JevEngine(folder,batch_size=3,concurrency=2)
            with patch('orgabm.engines.urllib.request.urlopen',side_effect=fake_http):
                result = run_simulation(organization_adapter(config()),engine,rounds=2,seed=7)
        self.assertEqual(result['decisions'],16)
        self.assertEqual(len(payloads),6)
        questions = {qid:q for payload in payloads for qid,q in payload['questions'].items()}
        self.assertEqual(len(questions),16)
        for qid, question in questions.items():
            a = int(qid.split('_a')[1])
            record = json.loads(question['instructions'].split('\n')[0])
            self.assertEqual(record['persona']['traits']['private_marker'],f'private-{a}')
            self.assertIn('organization',record)


class PersonaHttpTests(unittest.TestCase):
    def test_import_preview_run_and_rejection(self):
        from orgabm.server import Handler
        server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        def post(path, body):
            request = Request(f'http://127.0.0.1:{server.server_port}{path}',
                              data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
            with urlopen(request,timeout=10) as response: return json.load(response)
        try:
            imported = post('/api/personas/import',{'text':'[{"persona":"Fictional engineer"}]','preset':'personahub'})
            self.assertEqual(imported['count'],1)
            preview = post('/api/workforce/preview',config())
            result = post('/api/run',config())
            self.assertEqual(preview['population_sha256'],result['population_sha256'])
            self.assertEqual(result['decisions'],16)
            with self.assertRaises(HTTPError) as error:
                post('/api/personas/import',{'path':'not-an-allowed-server-path'})
            self.assertEqual(error.exception.code,400)
            error.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == '__main__': unittest.main()
