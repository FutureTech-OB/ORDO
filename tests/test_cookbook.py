"""Cookbook integration contracts: controls, information use and frozen people."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from examples.cookbook.recipes import disclosure_plan, information_rule, assignment_job, occupancy_fixture
from examples.cookbook.run import run_recipe
from orgabm.plans import expand_plan
from orgabm.placement import assign_personas
from orgabm.staged import run_staged_simulation
from orgabm.workflow_mesa import WorkflowModel, workflow_rule
from orgabm.workforce import workforce_metadata


def simulate(policy, engine):
    config = expand_plan(disclosure_plan(policy))['configs'][0]
    return run_staged_simulation(WorkflowModel(config),engine,rounds=config['rounds'],seed=config['seed'])


class CookbookTests(unittest.TestCase):
    def test_disclosure_changes_only_access_not_people_tasks_or_report_content(self):
        plans = [disclosure_plan(p) for p in ('manager_only','shared_now','shared_round_3')]
        bases = []
        contents = []
        for plan in plans:
            base=copy.deepcopy(plan['base'])
            memory=base.pop('memory')
            bases.append(base)
            contents.append([t['nodes'][0]['content'] for t in memory['trees']])
        self.assertEqual(bases[0],bases[1]); self.assertEqual(bases[1],bases[2])
        self.assertEqual(contents[0],contents[1]); self.assertEqual(contents[1],contents[2])

    def test_information_rule_has_no_hidden_report_access(self):
        private=expand_plan(disclosure_plan('manager_only'))['configs'][0]
        public=expand_plan(disclosure_plan('shared_now'))['configs'][0]
        private_model,public_model=WorkflowModel(private),WorkflowModel(public)
        a,b=private_model.prepare_stage(1,'proposal'),public_model.prepare_stage(1,'proposal')
        qid='t1_proposal_a1'  # Its first project is a low-value opportunity after due diligence.
        engine=information_rule()
        self.assertEqual(engine.decide(a.state,{qid:a.questions[qid]})[qid]['request'],1)
        self.assertEqual(engine.decide(b.state,{qid:b.questions[qid]})[qid]['abandon'],1)
        modified=copy.deepcopy(private)
        modified['memory']['trees'][0]['nodes'][0]['content']='{"estimates": {"project_0_1": 1.0}}'
        hidden=WorkflowModel(modified).prepare_stage(1,'proposal')
        self.assertEqual(a.questions[qid],hidden.questions[qid])

    def test_memory_blind_control_keeps_all_round_metrics_identical(self):
        results=[simulate(p,workflow_rule('permissive')) for p in ('manager_only','shared_now','shared_round_3')]
        self.assertEqual(results[0]['metrics'],results[1]['metrics'])
        self.assertEqual(results[1]['metrics'],results[2]['metrics'])

    def test_shared_information_reduces_requests_under_declared_rule(self):
        private=simulate('manager_only',information_rule())['metrics'][-1]
        public=simulate('shared_now',information_rule())['metrics'][-1]
        self.assertLess(public['cumulative']['requests'],private['cumulative']['requests'])
        self.assertLess(public['cumulative']['queue_wait_ticks'],private['cumulative']['queue_wait_ticks'])

    def test_constructed_population_survives_institution_change(self):
        result=assign_personas(assignment_job('stream'),occupancy_fixture())
        self.assertEqual(result['status'],'complete')
        first=WorkflowModel(result['config'])
        alternative=copy.deepcopy(result['config']); alternative['delegation_limit']=2
        second=WorkflowModel(alternative)
        self.assertEqual(first.roster,second.roster)
        self.assertEqual(workforce_metadata(first.config,first.roster)['population_sha256'],
                         workforce_metadata(second.config,second.roster)['population_sha256'])
        unfilled=assign_personas(assignment_job('stream',.95),occupancy_fixture())
        self.assertEqual(unfilled['status'],'incomplete'); self.assertIsNone(unfilled['config'])

    def test_export_is_nonexecuting_and_does_not_mislabel_custom_rule(self):
        with tempfile.TemporaryDirectory() as temp, patch('examples.cookbook.run.execute_plan',side_effect=AssertionError('Must not run')):
            root=Path(temp)/'03'
            run_recipe('03',root,export_only=True)
            aware=root/'manager_only__information_rule'
            self.assertTrue((aware/'case.json').is_file()); self.assertFalse((aware/'plan.json').exists())
            self.assertEqual(json.loads((aware/'jev-plan.json').read_text())['decision']['provider'],'jev')
            control=root/'manager_only__memory_blind_control'
            self.assertEqual(json.loads((control/'plan.json').read_text())['decision']['rule'],'permissive')
            self.assertFalse((control/'jev-plan.json').exists())


if __name__=='__main__': unittest.main()
