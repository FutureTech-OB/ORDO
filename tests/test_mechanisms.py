import json
from pathlib import Path
import unittest
import uuid
import numpy as np
from orgabm import kernel
from orgabm.experiment import run
from orgabm.organization import (validate_config, memberships, contact_sets, observation,
                               apply_round, effective_policy, rule_probabilities)


class Mechanisms(unittest.TestCase):
    def config(self, **changes):
        return validate_config(dict(agents=16, rounds=3, seed=7, departments=4, **changes))

    def world(self, config):
        return kernel.initialize(config['agents'], config['seed'], {'id':'test', 'guidance':False, 'penalty':0}, 'best')

    def test_contact_restrictions(self):
        c=self.config(contact='siloed');labels=memberships(c)
        for a, peers in enumerate(contact_sets(c, labels, 1)):
            self.assertNotIn(a,peers); self.assertEqual(len(set(peers)),3)
            self.assertTrue(all(labels[a]==labels[b] for b in peers))
        c['contact']='bridge'
        for a, peers in enumerate(contact_sets(c,labels,1)):
            self.assertEqual(sum(labels[a]!=labels[b] for b in peers),1)

    def test_hidden_payoffs_and_identities_do_not_leak(self):
        c=self.config(anonymous=True);w=self.world(c);labels=memberships(c);peers=contact_sets(c,labels,1)
        scores=kernel.landscape(7)
        r=observation(w,scores,c,labels,peers,0,1)
        visible={w['positions'][a] for a in [0]+peers[0]}
        altered=scores.copy()
        for x in range(len(scores)):
            if x not in visible: altered[x]=1000
        self.assertEqual(r,observation(w,altered,c,labels,peers,0,1))
        self.assertIsNone(r['department'])
        self.assertTrue(all('department' not in p for p in r['coworkers']))

    def test_approval_blocks_adoption_without_changing_proposal(self):
        c=self.config(approval_gain=10);w=self.world(c);w['positions']=list(range(16))
        scores=np.arange(2**kernel.LENGTH,dtype=float);labels=memberships(c)
        peers=contact_sets(c,labels,1);peers[0]=[1,2,3]
        actions=['copy_0']+['keep']*15
        m=apply_round(w,scores,c,labels,peers,actions,None,1)
        self.assertEqual(w['positions'][0],0);self.assertEqual(m['approval_denials'],1)
        self.assertEqual(w['histories'][0][-1]['requested_action'],'copy_0')
        self.assertTrue(w['histories'][0][-1]['approval_denied'])

    def test_synchronous_copy_uses_old_state(self):
        c=self.config();w=self.world(c);w['positions']=list(range(16));scores=np.arange(2**kernel.LENGTH,dtype=float)
        peers=contact_sets(c,memberships(c),1);peers[0]=[15,2,3];peers[1]=[0,2,3]
        apply_round(w,scores,c,memberships(c),peers,['copy_0','copy_0']+['keep']*14,None,1)
        self.assertEqual(w['positions'][:2],[15,1])

    def test_penalty_schedule_and_actual_accounting(self):
        c=self.config(penalty=10,intervention_round=2);w=self.world(c);labels=memberships(c)
        scores=np.ones(2**kernel.LENGTH)*20
        for t in [1,2]:apply_round(w,scores,c,labels,contact_sets(c,labels,t),['explore']*16,None,t)
        self.assertEqual(w['metrics'][0]['net_flow'],20)
        self.assertEqual(w['metrics'][1]['net_flow'],10)
        self.assertEqual(w['balances'][0],30)

    def test_advisory_guidance_not_hardcoded_in_rules(self):
        a=run(self.config());b=run(self.config(guidance=True))
        self.assertEqual(a['final_positions'],b['final_positions'])
        self.assertEqual(a['final_balances'],b['final_balances'])
        self.assertEqual(a['initial_state_sha256'],b['initial_state_sha256'])

    def test_repeated_run_is_deterministic(self):
        a=run(self.config(contact='bridge'));b=run(self.config(contact='bridge'))
        for key in ['metrics','final_positions','final_balances','traces']:
            self.assertEqual(a[key],b[key])

    def test_fresh_decisions_and_round_barriers(self):
        class Spy:
            def __init__(self):self.ids=[]
            def decide(self,state,questions):
                self.ids.append(list(questions))
                return {q:{'keep':1} for q in questions}
            def usage(self):return {'test_only':True}
        spy=Spy();result=run(self.config(engine='jev'),engine=spy)
        self.assertEqual([len(x) for x in spy.ids],[16,16,16])
        self.assertEqual(len({x for group in spy.ids for x in group}),48)
        self.assertTrue(all(x.startswith(f't{t}_') for t,g in enumerate(spy.ids,1) for x in g))
        self.assertFalse(result['probability_reuse'])

    def test_reject_missing_decision_before_advancing_round(self):
        class Missing:
            def decide(self,state,questions):return {}
        with self.assertRaises(ValueError):run(self.config(engine='jev'),engine=Missing())

    def test_bad_configs_and_live_web_requests_rejected(self):
        for bad in [{'agents':3},{'departments':50},{'penalty':float('nan')},{'contact':'unknown'},
                    {'agents':True},{'rounds':1,'intervention_round':2},{'unknown':2}]:
            with self.assertRaises(ValueError):validate_config(bad)
        with self.assertRaises(ValueError):validate_config({'engine':'jev'},web=True)

    def test_archive_is_complete_and_counts_are_consistent(self):
        root=Path(__file__).resolve().parents[1]
        data=json.loads((root/'examples/archived_pilot.json').read_text(encoding='utf-8'))
        self.assertEqual(sum(w['n']*len(w['metrics']) for w in data['worlds']),144000)
        self.assertEqual(len({w['seed'] for w in data['worlds']}),3)
        self.assertTrue(data['summary']['audit']['all_state_transitions_and_balances_replayed'])

    def test_cli_artifact_contains_replayable_actions(self):
        tmp=Path(__file__).resolve().parents[1]/'runs'/('test-'+uuid.uuid4().hex)
        tmp.mkdir(parents=True)
        result=run(self.config(),output=tmp)
        rows=[json.loads(x) for x in (tmp/'trajectory.jsonl').read_text().splitlines()]
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[-1]['positions_after'],result['final_positions'])
        self.assertIn('experiment.py',result['source_hashes'])


if __name__=='__main__':unittest.main()
