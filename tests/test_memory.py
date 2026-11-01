import copy
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from orgabm.memory import MemoryForest,validate_memory
from orgabm.personas import digest
from orgabm.plans import expand_plan
from orgabm.templates import workflow_plan
from orgabm.workforce import build_workforce
from orgabm.workflow import labels
from orgabm.workflow_mesa import WorkflowModel,workflow_rule
from orgabm.staged import run_staged_simulation


def fixture():
    c=expand_plan(workflow_plan('memory_permissions'))['configs'][0]
    return c,build_workforce(c,labels(c))


def by_node(view):
    return {(n['tree_id'],n['node_id']):n for n in view['items']}


class MemoryTests(unittest.TestCase):
    def test_scope_ownership_and_manager_are_not_omniscient(self):
        c,roster=fixture();forest=MemoryForest(c['memory'],roster)
        employee,_=forest.observe(1,1);manager,_=forest.observe(0,1);other_manager,_=forest.observe(4,1)
        self.assertIn(('member-1','private-note'),by_node(employee))
        self.assertNotIn(('member-1','private-note'),by_node(manager))
        self.assertIn(('department-0','incident'),by_node(manager))
        self.assertNotIn(('department-0','incident'),by_node(other_manager))
        self.assertNotIn('Previous delivery',json.dumps(other_manager,ensure_ascii=False))
        self.assertIn(('organization','restricted-detail'),by_node(manager))
        self.assertNotIn('Discussion attachment',json.dumps(employee,ensure_ascii=False))

    def test_summary_and_detail_releases_do_not_leak_other_levels(self):
        c,roster=fixture();forest=MemoryForest(c['memory'],roster)
        first,_=forest.observe(1,1);summary,_=forest.observe(1,3);detail,_=forest.observe(1,5)
        self.assertNotIn('Customer demand report',json.dumps(first,ensure_ascii=False))
        item=by_node(summary)[('organization','demand')]
        self.assertEqual(item['level'],'summary');self.assertNotIn('content',item)
        self.assertNotIn('a major customer',json.dumps(summary,ensure_ascii=False))
        self.assertIn('a major customer',by_node(detail)[('organization','demand')]['content'])
        self.assertNotIn('grants',json.dumps(detail));self.assertNotIn('from_round',json.dumps(detail))

    def test_selectors_intersect_fields_and_union_list_entries(self):
        c,roster=fixture()
        tree=c['memory']['trees'][1]
        tree['readers']=[{'departments':[0],'roles':['manager']},{'agents':[5]}]
        forest=MemoryForest(c['memory'],roster)
        for agent,allowed in [(0,True),(1,False),(4,False),(5,True)]:
            view,_=forest.observe(agent,1)
            self.assertEqual(('department-0','department-root') in by_node(view),allowed)

    def test_default_deny_and_ancestor_caps(self):
        c,roster=fixture()
        nodes=[dict(id='root',title='hidden root'),dict(id='child',parent='root',title='hidden child',
            content='secret',grants=[dict(audience=[{'everyone':True}],level='detail')])]
        policy={'trees':[dict(id='tree',scope='organization',nodes=nodes)]}
        view,_=MemoryForest(policy,roster).observe(1,1)
        self.assertEqual(view,{'items':[]})
        nodes[0]['grants']=[dict(audience=[{'everyone':True}],level='summary')]
        view,_=MemoryForest(policy,roster).observe(1,1)
        self.assertEqual([n['level'] for n in view['items']],['summary','summary'])
        self.assertNotIn('secret',json.dumps(view))
        nodes[1].pop('grants')
        self.assertEqual(MemoryForest(policy,roster).observe(1,1)[0],view)
        nodes[1]['grants']=[]
        self.assertEqual(len(MemoryForest(policy,roster).observe(1,1)[0]['items']),1)

    def test_round_windows_and_organization_boundary(self):
        c,roster=fixture();policy=c['memory']
        policy['trees'][2]['nodes'][0]['grants'][0].update(from_round=2,until_round=3)
        forest=MemoryForest(policy,roster)
        for tick,allowed in [(1,False),(2,True),(3,True),(4,False)]:
            self.assertEqual(('member-1','private-note') in by_node(forest.observe(1,tick)[0]),allowed)
        view,audit=forest.observe(1,3,organization_id='another-org')
        self.assertEqual(view,{'items':[]});self.assertEqual(audit['eligible_count'],0)

    def test_budget_omission_is_distinct_from_permission_and_stays_bounded(self):
        c,roster=fixture();policy=c['memory'];policy['max_items']=1
        forest=MemoryForest(policy,roster);view,audit=forest.observe(0,1)
        self.assertEqual(len(view['items']),1);self.assertGreater(audit['budget_omitted'],0)
        self.assertEqual(audit['view_sha256'],digest(view))
        self.assertEqual(audit['view_chars'],len(json.dumps(view,ensure_ascii=False)))
        policy['max_items']=200;policy['max_chars']=128
        view,audit=MemoryForest(policy,roster).observe(0,1)
        self.assertLessEqual(len(json.dumps(view,ensure_ascii=False)),128)
        self.assertGreater(audit['budget_omitted'],0)

    def test_bad_policies_are_rejected(self):
        c,roster=fixture();policy=c['memory'];cases=[]
        def case(edit):
            p=copy.deepcopy(policy);edit(p);cases.append(p)
        case(lambda p:p.update(max_items=0))
        case(lambda p:p['trees'].append(copy.deepcopy(p['trees'][0])))
        case(lambda p:p['trees'][1].update(owner=999))
        case(lambda p:p['trees'][0].update(readers=[{'agents':[True]}]))
        case(lambda p:p['trees'][0].update(readers=[{'roles':['unknown']}]))
        case(lambda p:p['trees'][0].update(readers=[{}]))
        case(lambda p:p['trees'][0].update(readers=[{'everyone':1}]))
        case(lambda p:p['trees'][0]['nodes'][0].update(parent='demand'))
        case(lambda p:p['trees'][0]['nodes'][0].update(parent='missing'))
        case(lambda p:p['trees'][0]['nodes'][0]['grants'][0].update(from_round=3,until_round=2))
        case(lambda p:p['trees'][0]['nodes'][0]['grants'][0].update(level='all'))
        case(lambda p:p['trees'][0]['nodes'][0]['grants'][0].update(level=[]))
        for p in cases:
            with self.subTest(policy=p),self.assertRaises(ValueError):validate_memory(p,roster)

    def test_input_and_view_mutation_do_not_change_store(self):
        c,roster=fixture();policy=c['memory'];forest=MemoryForest(policy,roster)
        expected=forest.observe(0,1)
        policy['trees'][0]['nodes'][0]['title']='changed outside'
        view,_=forest.observe(0,1);view['items'][0]['title']='changed returned view'
        self.assertEqual(forest.observe(0,1),expected)
        with self.assertRaises(ValueError):forest.observe(True,1)
        with self.assertRaises(ValueError):forest.observe(1000,1)

    def test_workflow_audit_matches_exact_inputs_and_replays(self):
        c,roster=fixture();forest=MemoryForest(c['memory'],roster)
        with tempfile.TemporaryDirectory() as tmp:
            model=WorkflowModel(c)
            result=run_staged_simulation(model,workflow_rule(),rounds=c['rounds'],seed=c['seed'],output=Path(tmp)/'world')
            events=[json.loads(x) for x in (Path(tmp)/'world'/'events.jsonl').read_text(encoding='utf-8').splitlines()]
            for event in events:
                if event['event']!='stage':continue
                self.assertNotIn('Fictional board',event['state'])
                for qid,question in event['questions'].items():
                    agent=event['agent_ids'][qid];o=json.loads(question['instructions'])
                    view,audit=forest.observe(agent,event['round'])
                    self.assertEqual(o['memory'],view)
                    self.assertEqual(event['effects']['memory_visibility'][str(agent)],audit)
                    self.assertNotIn('eligible_count',question['instructions'])
            again=run_staged_simulation(WorkflowModel(c),workflow_rule(),rounds=c['rounds'],seed=c['seed'])
            self.assertEqual(result['metrics'],again['metrics'])

    def test_jev_http_questions_receive_only_the_member_view(self):
        from orgabm.engines import JevEngine
        c,roster=fixture();c['rounds']=3
        forest=MemoryForest(c['memory'],roster);observed=[]
        def respond(request,timeout):
            payload=json.loads(request.data)
            self.assertNotIn('Fictional board',payload['state'])
            for question in payload['questions'].values():
                o=json.loads(question['instructions']);observed.append(o)
                self.assertEqual(o['memory'],forest.observe(o['member']['agent'],o['round'])[0])
            answers=workflow_rule().decide(payload['state'],payload['questions'])
            return io.BytesIO(json.dumps({'model':'jev-1.14.0','usage':{'input_tokens':10},
                'answers':{q:{'probabilities':p} for q,p in answers.items()}}).encode())
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'TYPESAFE_API_KEY':'test-only-placeholder'}),patch('urllib.request.urlopen',side_effect=respond):
            engine=JevEngine(tmp,batch_size=4,concurrency=1)
            run_staged_simulation(WorkflowModel(c),engine,rounds=3,seed=c['seed'])
        self.assertTrue(any(o['member']['role']=='manager' for o in observed))
        self.assertTrue(any(o['member']['role']=='employee' for o in observed))

    def test_browser_memory_preview_enforces_member_permissions(self):
        from orgabm.server import Handler
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            url=f'http://127.0.0.1:{server.server_port}/api/workflow/memory-preview'
            body=dict(plan=workflow_plan('memory_permissions'),agent=4,round_no=1)
            def request():
                return urllib.request.Request(url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(request()) as response:result=json.load(response)
            self.assertNotIn('department-0',json.dumps(result['view']))
            body['agent']=999
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request())
            self.assertEqual(error.exception.code,400)
        finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
