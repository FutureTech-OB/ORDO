import ast
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from orgabm.sdk import run_simulation
from examples.nc_polarization_live.protocol import AuthorPrompts,HybridPolarization,TOPIC,selected_text
from examples.nc_polarization_live.content import decode_text


class FakeContent:
    def __init__(self):self.rows=[]
    def generate(self,event,kind,prompt):
        self.rows.append((event,kind,prompt))
        return 'Fresh '+kind+' '+event


class FixedEngine:
    def __init__(self):self.inputs=[]
    def decide(self,state,questions):
        self.inputs.append(copy.deepcopy(questions))
        return {qid:{k:float(k==('-2' if '-2' in q['criteria'] else 'yes')) for k in q['criteria']}
                for qid,q in questions.items()}
    def usage(self):return dict(recorded_input_cost_usd=0)


@unittest.skipUnless(Path('.buildtmp/nc-polarization-code/utils.py').exists(),'Pinned upstream sources not cached')
class HybridTests(unittest.TestCase):
    def setUp(self):
        self.prompts=AuthorPrompts('.buildtmp/nc-polarization-code/utils.py')
        self.initial=dict(states=[-2,0,1,2],edges=[[0,1],[1,2],[2,3],[3,0]])

    def test_exact_author_prompt_has_local_reasons(self):
        p=dict(side=-2,reasons='private reason',patience=0)
        text=self.prompts.get('LLM_update_profile_5_and_LLM_get_reason',p,'fresh incoming','older',TOPIC)
        self.assertIn('<<<private reason>>>',text);self.assertIn('<<<fresh incoming>>>',text)
        self.assertNotIn('older',text)

    def test_preserve_author_unusual_message_selection(self):
        messages=[dict(content=str(i)) for i in range(7)]
        self.assertEqual(selected_text(messages,[]),('06543',''))

    def test_spread_matches_independent_author_function_including_target_zero(self):
        world=HybridPolarization(self.initial,self.prompts,FakeContent(),seed=2)
        world.users[0]['messages']=[dict(source=0,target=0,content='zero broadcasts'),dict(source=0,target=1,content='direct')]
        world.users[2]['messages']=[dict(source=2,target=None,content='broadcast')]
        objects=[SimpleNamespace(node_id=i,message_list=copy.deepcopy(u['messages']),
            previous_message=copy.deepcopy(u['previous']),friend_pool=copy.deepcopy(u['friends'])) for i,u in enumerate(world.users)]
        tree=ast.parse(Path('.buildtmp/nc-polarization-code/simulate.py').read_text())
        spread=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='spread')
        namespace=dict(user_list=objects,copy=copy)
        exec(compile(ast.Module(body=[spread],type_ignores=[]),'independent_author_spread','exec'),namespace)
        expected=sorted(set(namespace['spread']()));actual=world._spread()
        self.assertEqual(actual,expected)
        for u,original in zip(world.users,objects):
            self.assertEqual(u['messages'],original.message_list);self.assertEqual(u['previous'],original.previous_message)

    def test_fresh_messages_feed_subsequent_state_and_exact_rerun(self):
        gen=FakeContent();world=HybridPolarization(self.initial,self.prompts,gen,seed=2,epochs=2)
        engine=FixedEngine();run=run_simulation(world,engine,rounds=7,seed=2)
        self.assertEqual(run['completed_rounds'],7);self.assertGreater(world.counts['generated_posts'],0)
        self.assertGreater(world.counts['delivered_messages'],0)
        self.assertTrue(any('Fresh reason' in q['instructions'] for batch in engine.inputs for q in batch.values()))
        self.assertTrue(any(m['content'].startswith('Fresh post') for u in world.users for m in u['messages']))
        again=HybridPolarization(self.initial,self.prompts,FakeContent(),seed=2,epochs=2)
        second=run_simulation(again,FixedEngine(),rounds=7,seed=2)
        self.assertEqual(run['metrics'],second['metrics']);self.assertEqual(world.users,again.users)


class ContentValidationTests(unittest.TestCase):
    def test_generator_cannot_reverse_jev_speaking_decision(self):
        with self.assertRaises(ValueError):decode_text('post',json.dumps(dict(will='no',message='text')))
        with self.assertRaises(ValueError):decode_text('reason','{"reasons":""}')
        self.assertEqual(decode_text('reason','{"reasons":["a","b"]}'),'ab')


if __name__=='__main__':unittest.main()
