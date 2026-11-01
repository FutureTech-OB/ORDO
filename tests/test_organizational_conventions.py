import json
import unittest

from orgabm.sdk import FunctionEngine,run_simulation
from examples.organizational_conventions.model import OrganizationalConventions,OrganizationEnsemble,rule_engine


def world(**kwargs): return OrganizationalConventions(agents=100,departments=5,committed=2,rounds=8,pairs_per_round=12,**kwargs)


class OrganizationalConventionTests(unittest.TestCase):
    def test_actual_hierarchy_and_population_are_shared_across_treatments(self):
        a=world(placement='employee'); b=world(placement='manager',message_mode='official')
        self.assertEqual(a.structure_sha256,b.structure_sha256); self.assertEqual(a.population_sha256,b.population_sha256)
        self.assertEqual(a.seed_departments,b.seed_departments)
        self.assertTrue(all(a.roster[i]['role']=='employee' for i in a.seed_ids))
        self.assertTrue(all(b.roster[i]['role']=='manager' for i in b.seed_ids))
        self.assertEqual(a.roster[20]['manager'],0); self.assertEqual(a.roster[21]['manager'],20)

    def test_permission_is_real_and_does_not_follow_manager_title_automatically(self):
        w=world(placement='employee',message_mode='official')
        writer=next(iter(w.seed_ids)); department=w.roster[writer]['department']
        self.assertEqual(w.publication_record(writer,department,official=True)['channel'],'official')
        manager=department*w.size
        with self.assertRaises(PermissionError):w.publication_record(manager,department,official=True)
        with self.assertRaises(PermissionError):w.publication_record(writer,(department+1)%w.departments)

    def test_matched_reach_peer_and_official_and_no_cross_department_leak(self):
        peer=world(message_mode='peer'); official=world(message_mode='official')
        for a in range(100):
            p,_=peer.memory.observe(a,1); o,_=official.memory.observe(a,1)
            self.assertEqual(bool(p['items']),bool(o['items']))
            self.assertEqual(bool(p['items']),peer.roster[a]['department'] in peer.seed_departments)
            if o['items']:self.assertEqual(json.loads(o['items'][0]['content'])['channel'],'official')
        self.assertEqual(official.memory.observe(0,1,organization_id='another-org')[0]['items'],[])

    def test_scheduled_disclosure_filters_before_inference(self):
        w=world(message_mode='official',release_round=3)
        a=next(a for a in range(100) if a not in w.seed_ids and w.roster[a]['department'] in w.seed_departments)
        self.assertEqual(w.local_record(a,0,1)[0]['bulletins'],[])
        self.assertEqual(w.local_record(a,0,3)[0]['bulletins'][0]['value'],'M')

    def test_pairs_are_disjoint_and_schedule_is_identical_under_policy_changes(self):
        a=world(); b=world(placement='manager',message_mode='official')
        for t in range(1,9):
            x=a.prepare(t); y=b.prepare(t)
            pairs=a.pending[1]; people=[p for pair in pairs for p in pair[:2]]
            self.assertEqual(len(people),len(set(people))); self.assertEqual(pairs,b.pending[1])
            self.assertEqual(len(x.agent_ids),len(set(x.agent_ids.values())))
            a.advance(t,{qid:'Q' for qid in x.questions},{})
            b.advance(t,{qid:'Q' for qid in y.questions},{})

    def test_guidance_does_not_force_voluntary_choices(self):
        w=world(message_mode='official')
        run_simulation(w,FunctionEngine(lambda s,q:{'Q':1,'M':0}),rounds=8,seed=3)
        self.assertTrue(all(w.last[a]=='Q' for a in range(w.n) if a not in w.seed_ids))
        self.assertTrue(all(w.last[a]=='M' for a in w.seed_ids))

    def test_history_window_and_question_information_boundary(self):
        w=world(message_mode='official'); run_simulation(w,rule_engine('uniform'),rounds=8,seed=3)
        batch=w.prepare(9)
        self.assertTrue(all(len(json.loads(q['instructions'])['history'])<=5 for q in batch.questions.values()))
        for q in batch.questions.values():
            self.assertNotIn('seed_ids',q['instructions']); self.assertNotIn('committed',q['instructions'])
            self.assertNotIn('voluntary_M_share',q['instructions'])

    def test_public_sdk_ensemble_keeps_worlds_isolated(self):
        env=OrganizationEnsemble({'a':world(),'b':world(message_mode='peer')})
        result=run_simulation(env,rule_engine('uniform'),rounds=2,seed=3)
        self.assertEqual(result['status'],'complete'); self.assertEqual(env.worlds['a'].round,2)
        self.assertEqual(env.latest['a']['schedule_sha256'],env.latest['b']['schedule_sha256'])


if __name__=='__main__':unittest.main()
