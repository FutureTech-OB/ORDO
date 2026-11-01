import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from orgabm.sdk import FunctionEngine
from orgabm.staged import run_staged_simulation
from orgabm.workflow import validate_workflow
from orgabm.plans import expand_plan
from orgabm.templates import workflow_plan
from orgabm.workflow_mesa import WorkflowModel, workflow_rule


def config(**updates):
    c=dict(agents=4,departments=1,rounds=6,seed=7,budget=30,
        tasks=[dict(id=f'task{i}',owner=i,effort=1,cost=2,value=8,signal=.8,success_probability=1) for i in [1,2,3]])
    c.update(updates)
    return c


def run(c,engine=None,output=None):
    model=WorkflowModel(c)
    result=run_staged_simulation(model,engine or workflow_rule(),rounds=model.config['rounds'],seed=model.config['seed'],output=output)
    return model,result


class WorkflowTests(unittest.TestCase):
    def test_authority_capacity_and_task_timing(self):
        central,r=run(config(rounds=2))
        delegated,d=run(config(rounds=2,delegation_limit=2))
        self.assertEqual(r['metrics'][0]['completed_tasks'],0)
        self.assertEqual(r['metrics'][0]['queue_length'],2)
        self.assertEqual(r['metrics'][1]['completed_tasks'],1)
        self.assertEqual(d['metrics'][0]['completed_tasks'],3)
        self.assertEqual(d['metrics'][-1]['cumulative']['requests'],0)
        self.assertEqual(central.steps,2)
        self.assertEqual(len(central.datacollector.get_model_vars_dataframe()),2)
        _,faster=run(config(rounds=2,review_capacity=3))
        self.assertEqual(faster['metrics'][1]['completed_tasks'],3)

    def test_dependencies_wait_for_completed_predecessors(self):
        c=config(delegation_limit=2)
        c['tasks'][1]['dependencies']=['task1']
        m,r=run(c)
        self.assertEqual(m.tasks['task1']['completed_at'],1)
        self.assertEqual(m.tasks['task2']['completed_at'],2)
        c['tasks'][0]['signal']=.1
        m,r=run(c)
        self.assertEqual(m.tasks['task1']['status'],'rejected')
        self.assertEqual(m.tasks['task2']['status'],'unstarted')
        self.assertEqual(r['metrics'][-1]['blocked_tasks'],1)

    def test_budget_and_rewards_conserve_resources(self):
        for weight in [0,.4,1]:
            c=config(budget=2,delegation_limit=2,individual_reward_weight=weight)
            m,r=run(c)
            self.assertEqual(m.spent,2)
            self.assertEqual(r['metrics'][-1]['completed_tasks'],1)
            self.assertAlmostEqual(sum(m.earnings),m.gross-m.spent)
            self.assertGreater(r['metrics'][-1]['cumulative']['budget_denials'],0)
        def reversed_answers(state,questions):
            return dict(reversed(list(workflow_rule().decide(state,questions).items())))
        class Reverse:
            decide=staticmethod(reversed_answers)
            def usage(self):return {}
        m1,_=run(config(budget=2,delegation_limit=2))
        m2,_=run(config(budget=2,delegation_limit=2),Reverse())
        self.assertEqual(m1.snapshot(),m2.snapshot())

    def test_revision_costs_capacity_and_requires_new_approval(self):
        c=config(tasks=[dict(id='a',owner=1,effort=1,cost=2,revision_effort=2)])
        rule=workflow_rule()
        def choose(state,q):
            o=json.loads(q['instructions'])
            if o['stage'].startswith('review') and o['task']['revisions']==0:
                return {a:float(a=='revise') for a in q['criteria']}
            return rule.function(state,q)
        m,r=run(c,FunctionEngine(choose))
        self.assertEqual(m.tasks['a']['revisions'],1)
        self.assertEqual(m.tasks['a']['completed_at'],5)
        self.assertEqual(m.spent,2)
        self.assertEqual(r['metrics'][-1]['cumulative']['revision_units'],2)
        self.assertEqual(r['metrics'][-1]['cumulative']['requests'],2)

    def test_deferred_shared_rewards_match_explicit_member_accounting(self):
        for weight in [0, .37, 1]:
            c=config(delegation_limit=2,individual_reward_weight=weight)
            c['tasks'][0].update(cost=1.3,value=7.7,effort=2)
            c['tasks'][1].update(cost=3.2,value=8.9,effort=1)
            c['tasks'][2].update(cost=.7,value=4.1,effort=3)
            model=WorkflowModel(c)
            expected=[0.0]*c['agents']
            original_reward=model._reward
            def check_transaction(owner,amount):
                original_reward(owner,amount)
                for agent in range(c['agents']):
                    expected[agent]+=(1-weight)*amount/c['agents']
                expected[owner]+=weight*amount
                for agent,balance in enumerate(expected):
                    self.assertAlmostEqual(model.earnings_for(agent),balance,places=10)
            model._reward=check_transaction
            rule=workflow_rule()
            def check_observation(state,question):
                member=json.loads(question['instructions'])['member']
                self.assertAlmostEqual(member['personal_earnings'],expected[member['agent']],places=10)
                return rule.function(state,question)
            result=run_staged_simulation(model,FunctionEngine(check_observation),rounds=c['rounds'],seed=c['seed'])
            self.assertEqual(result['metrics'][-1]['completed_tasks'],3)
            for actual,balance in zip(model.snapshot()['earnings'],expected):
                self.assertAlmostEqual(actual,balance,places=10)

    def test_large_organization_plan_is_valid_and_multilevel(self):
        from examples.large_organization import large_organization_plan
        from orgabm.workforce import build_workforce
        from orgabm.workflow import labels
        plan=large_organization_plan(1000)
        c=expand_plan(plan)['configs'][0]
        roster=build_workforce(c,labels(c))
        self.assertEqual(len(roster),1000)
        self.assertEqual(len(c['tasks']),900)
        self.assertEqual(len({r['department'] for r in roster}),100)
        node,levels=999,1
        while roster[node]['manager'] is not None:
            node=roster[node]['manager'];levels+=1
        self.assertGreaterEqual(levels,4)

    def test_local_information_and_phase_causality(self):
        c=config(population={'records':[{'id':f'p{i}','description':f'private-person-{i}','source':{'secret':'provenance'}} for i in range(4)],'sampling':'ordered'})
        m=WorkflowModel(c)
        b=m.prepare_stage(1,'proposal')
        self.assertNotIn('success_probability',json.dumps(b.questions))
        self.assertNotIn('provenance',json.dumps(b.questions))
        self.assertNotIn('private-person-0',json.dumps(b.questions))
        with self.assertRaises(ValueError):m.prepare_stage(1,'review_0')
        with self.assertRaises(ValueError):m.advance_stage(1,'proposal',{q:'approve' for q in b.questions},{})
        self.assertTrue(all(t['status']=='unstarted' for t in m.tasks.values()))
        m.advance_stage(1,'proposal',{q:'request' for q in b.questions},{})
        review=m.prepare_stage(1,'review_0')
        o=json.loads(next(iter(review.questions.values()))['instructions'])
        self.assertEqual(o['task']['requested_at'],1)
        self.assertEqual(o['member']['persona']['description'],'private-person-0')
        self.assertNotIn('private-person-1',json.dumps(review.questions))
        self.assertNotIn('success_probability',json.dumps(review.questions))

    def test_failed_later_stage_retains_evidence_without_completed_round(self):
        class Broken:
            def decide(self,state,questions):
                if 'review' in next(iter(questions)):return {}
                return workflow_rule().decide(state,questions)
            def usage(self):return {}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'world';m=WorkflowModel(config())
            with self.assertRaises(ValueError):run_staged_simulation(m,Broken(),rounds=2,seed=7,output=path)
            result=json.loads((path/'result.json').read_text())
            self.assertEqual(result['completed_rounds'],0)
            self.assertEqual(result['completed_stages'],1)
            self.assertEqual(result['active_stage'],'review_0')
            self.assertEqual(len((path/'events.jsonl').read_text().splitlines()),1)
            self.assertEqual(m.steps,0)

    def test_validation_rejects_invalid_graphs_and_missing_authority(self):
        cases=[]
        c=config();c['tasks'][0]['dependencies']=['unknown'];cases.append(c)
        c=config();c['tasks'][0]['dependencies']=['task2'];c['tasks'][1]['dependencies']=['task1'];cases.append(c)
        c=config();c['tasks'][0]['owner']=0;cases.append(c)
        cases += [config(review_capacity=0),config(budget=float('nan')),config(structure={'template':'flat'}),config(engine='best')]
        for c in cases:
            with self.subTest(c=c), self.assertRaises(ValueError):validate_workflow(c)
        m=WorkflowModel(config())
        with self.assertRaises(ValueError):m.step()

    def test_top_authority_is_distinct_from_direct_supervisor(self):
        from orgabm.workflow import ROLES,reviewer_for
        from orgabm.workforce import build_workforce
        structure={'template':'custom','roles':ROLES,'assignments':[
            {'agent':0,'department':0,'role':'manager','manager':None},
            {'agent':1,'department':0,'role':'manager','manager':0},
            {'agent':2,'department':0,'role':'employee','manager':1},
            {'agent':3,'department':0,'role':'employee','manager':1}]}
        c=validate_workflow(config(structure=structure,tasks=[dict(id='a',owner=2)]))
        roster=build_workforce(c,[0]*4)
        self.assertEqual(reviewer_for(roster,2,'direct'),1)
        self.assertEqual(reviewer_for(roster,2,'top'),0)

    def test_jev_batches_are_stage_local_and_counts_are_bounded(self):
        from orgabm.engines import JevEngine
        plan={'scenario':'task_workflow','base':{k:v for k,v in config(rounds=2,review_capacity=2).items() if k!='seed'},
            'seeds':[7],'decision':{'provider':'jev','batch_size':2}}
        expanded=expand_plan(plan);payloads=[]
        def respond(req,timeout):
            p=json.loads(req.data);payloads.append(p)
            answers=workflow_rule().decide(p['state'],p['questions'])
            return io.BytesIO(json.dumps({'model':'jev-1.14.0','usage':{'input_tokens':10},
                'answers':{q:{'probabilities':v} for q,v in answers.items()}}).encode())
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'TYPESAFE_API_KEY':'test-only-placeholder'}),patch('urllib.request.urlopen',side_effect=respond):
            engine=JevEngine(tmp,batch_size=2,concurrency=1)
            m,r=run(expanded['configs'][0],engine)
        self.assertLessEqual(engine.requests,expanded['provider_requests'])
        self.assertLessEqual(r['decisions'],expanded['decisions'])
        ids=[]
        for payload in payloads:
            obs=[json.loads(q['instructions']) for q in payload['questions'].values()]
            self.assertEqual(len({(o['round'],o['stage']) for o in obs}),1)
            self.assertLessEqual(len(obs),2)
            ids.extend(payload['questions'])
        self.assertEqual(len(ids),len(set(ids)))
        self.assertTrue(any('review_1' in q for q in ids))

    def test_replay_saved_probabilities_reproduces_rounds(self):
        c=config(review_capacity=2)
        with tempfile.TemporaryDirectory() as tmp:
            _,original=run(c,output=Path(tmp)/'world')
            events=[json.loads(x) for x in (Path(tmp)/'world'/'events.jsonl').read_text().splitlines()]
            p={q:probs for e in events if e['event']=='stage' for q,probs in e['probabilities'].items()}
            replay=FunctionEngine(lambda state,q:{})
            replay.decide=lambda state,questions:{q:p[q] for q in questions}
            _,again=run(c,replay)
            self.assertEqual(original['metrics'],again['metrics'])

    def test_assignment_can_prepare_workflow_personas(self):
        from orgabm.placement import assign_personas
        c=config(population={'records':[{'id':str(i),'description':'fictional'} for i in range(8)]})
        job={'scenario':'task_workflow','config':c,'threshold':.5}
        r=assign_personas(job,FunctionEngine(lambda s,q:{'holds_position':.5,'does_not_hold_position':.5}))
        self.assertEqual(r['status'],'complete')
        m,simulation=run(r['config'])
        self.assertEqual(len(m.roster),4)
        self.assertTrue(all(row['persona']['source']['orgabm_assignment']['probability']==.5 for row in m.roster))

    def test_service_and_browser_validation(self):
        from orgabm.mcp_server import ExperimentService
        from orgabm.server import browser_workflow_preview
        plan=workflow_plan();plan['seeds']=[7];plan['base']['review_capacity']=2
        with tempfile.TemporaryDirectory() as tmp:
            service=ExperimentService(tmp)
            try:
                job=service.start(plan);service.jobs[job['id']].result(timeout=30)
                status=service.get(job['id'])
                self.assertEqual(status['status'],'complete')
                self.assertEqual(status['completed_worlds'],2)
                trace=service.inspect(job['id'],0,1,0,'review_0')
                self.assertEqual(trace['proposed_action'],'approve')
                with self.assertRaises(ValueError):service.inspect(job['id'],0,1,0)
                self.assertTrue(Path(status['results'][0]['state_file']).is_file())
            finally:service.pool.shutdown()
        self.assertEqual(browser_workflow_preview(plan)['worlds'],2)
        with self.assertRaises(ValueError):browser_workflow_preview({**plan,'decision':{'provider':'jev'}})
        with self.assertRaises(ValueError):browser_workflow_preview({**plan,'decision':'invalid'})


if __name__=='__main__':unittest.main()
