"""Pause the pinned author loop at its LLM boundary; retain its world dynamics.

Only imports, file transport, progress output and LLM transport are replaced.
The original run_simulation is the independent offline reference.  The SDK
version adds two yields per year, preserving the original task/update loops.
"""
import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import random
import time
from types import SimpleNamespace

from orgabm.sdk import DecisionBatch

UPSTREAM = Path(__file__).parent / 'upstream'
SOURCE = UPSTREAM / 'LLMABM-GitHub-WRR.py'
COMMIT = '6952c793b3b3c0b0c0adfabc6e34062146d351da'
EXPECTED_BLOB = '099e1fc0c6328b5f9eb459bbee28b96cdb14d779'
PAPER_ID = 'yang_chiou_wrr_2026'


def locked_source():
    data = SOURCE.read_bytes()
    blob = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    if blob != EXPECTED_BLOB:
        raise ValueError('Pinned author source changed: '+blob)
    return data.decode('utf-8')


class Template:
    @staticmethod
    def from_template(value):
        return value


def namespace(seed, *, paused=False, choose=None, flood_years=(3, 4, 9), appraisals=False):
    """Compile reviewed author definitions without importing Ollama or running main.

The warm-start CSV transport is replaced by in-memory objects generated using
the author's initialization function.  No author decisions are supplied.
"""
    tree = ast.parse(locked_source())
    tree.body = [n for n in tree.body if not isinstance(n, (ast.Import, ast.ImportFrom, ast.If))]
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    fn = functions['run_simulation']
    past_node = next(n for n in fn.body if isinstance(n, ast.Assign)
                     and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'past_events')
    past_events = ast.literal_eval(past_node.value)
    if paused:
        context = next(n for n in fn.body if isinstance(n, ast.With))
        year_loop = context.body[0]
        batch_loop = next(n for n in year_loop.body if isinstance(n, ast.For)
                          and isinstance(n.target, ast.Name) and n.target.id == 'i')
        before = ast.parse("responses_all = yield {'kind': 'decisions', 'year': year, 'tasks': tasks_to_process}").body[0]
        year_loop.body.insert(year_loop.body.index(batch_loop), before)
        calls = []
        for n in ast.walk(batch_loop):
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute):
                if isinstance(n.value.func.value, ast.Name) and n.value.func.value.id == 'llm' and n.value.func.attr == 'batch':
                    n.value = ast.parse('responses_all[i:i + BATCH_SIZE]', mode='eval').body
                    calls.append(n)
        if len(calls) != 1:
            raise ValueError('Author LLM boundary changed.')
        year_loop.body += ast.parse("yield {'kind': 'year_end', 'year': year, 'agents': agents, 'logs': logs, 'flood_event': flood_event, 'grant_available': grant_available}").body
    rng = random.Random(seed)
    class Model:
        def __init__(self, **kwargs):
            self.count = 0
            self.prompts = []
        def batch(self, prompts):
            if choose is None:
                raise RuntimeError('No implicit decision model or fallback is permitted.')
            self.prompts.extend(prompts)
            out = []
            for prompt in prompts:
                code = str(choose(prompt, self.count))
                self.count += 1
                prefix = ('Threat Appraisal: Offline test text, not an inferred inner state.\n'
                          'Coping Appraisal: A different logged string.\n') if appraisals else ''
                out.append(prefix+'Final Decision: '+code)
            return out
    model = Model()
    ns = dict(random=rng, time=time, PromptTemplate=Template,
              OllamaLLM=lambda **kwargs: model,
              tqdm=lambda value, **kwargs: value,
              open=lambda *args, **kwargs: io.StringIO(),
              print=lambda *args, **kwargs: None,
              os=SimpleNamespace(path=SimpleNamespace(exists=lambda path: True)),
              pd=SimpleNamespace(read_csv=lambda path: {'Flood_Years': list(flood_years)}))
    exec(compile(ast.fix_missing_locations(tree), str(SOURCE), 'exec'), ns)
    initial = ns['initialize_agents_randomly'](past_events)
    ns['load_agents_from_file'] = lambda *args: copy.deepcopy(initial)
    ns['_initial_agents'] = initial
    ns['_model'] = model
    return ns


class FloodEnvironment:
    """100 households, original 10-year calendar and all original choice sets."""
    def __init__(self, seed):
        self.seed = seed
        self.ns = namespace(seed, paused=True)
        self.generator = self.ns['run_simulation']()
        self.agents = copy.deepcopy(self.ns['_initial_agents'])
        self.logs = []
        self.pending = None
        self.round = 0
        self.source_ended = False
        self.actual_years = 0

    def describe(self):
        return dict(model='original_llm_flood_adaptation_external_decision',
                    paper_id=PAPER_ID, doi='10.1029/2025WR042111',
                    original_llm='gemma3:4b', original_commit=COMMIT,
                    source_blob=EXPECTED_BLOB, source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                    agents=100, years=10, flood_years=[3, 4, 9], seed=self.seed,
                    grant_probability=.5, random_memory_recall_probability=.2,
                    memory_window=5, original_batch_size=25,
                    topology='Complete-population neighborhood: all other 99 households, aggregate elevated/relocated shares.',
                    initialization='Author random-profile function; new declared seed, not archived original profiles.',
                    replacement='Only original llm.batch decisions become freshly sampled Jev categorical choices. Appraisal strings remain empty and are not fed back.',
                    retained='Original prompt including inaction prior, state-dependent 4/3 actions, annual task construction, ordered updates, trust, flood exposure, physical elevation risk reduction, grants, memory and terminal relocation.',
                    scope='Figure 2 LLM-arm protocol; not original Gemma outputs, traditional comparator, reasoning analysis, prompt/memory/model sensitivity figures or human validation.')

    def prepare(self, t):
        if t != self.round+1 or self.pending is not None or not 1 <= t <= 10:
            raise ValueError('Unexpected annual order.')
        if self.source_ended:
            self.pending = []
            return DecisionBatch('', {}, {})
        try:
            event = next(self.generator)
        except StopIteration as end:
            self.source_ended = True
            self.agents, self.logs = end.value[0:2]
            self.pending = []
            return DecisionBatch('', {}, {})
        if event['kind'] != 'decisions' or event['year'] != t:
            raise ValueError('Unexpected author-loop boundary.')
        self.pending = event['tasks']
        questions, agents = {}, {}
        for task in self.pending:
            agent = task['agent']
            qid = f"year{t}_{agent['id']}"
            mapping = self.ns['DECISION_MAP_ELEVATED' if task['was_elevated'] else 'DECISION_MAP_NOT_ELEVATED']
            questions[qid] = dict(type='choice', instructions=task['prompt'], criteria=dict(mapping))
            agents[qid] = agent['id']
        return DecisionBatch('Predict this household\'s final decision under the original scenario. '
                             'Supply probabilities for the available action codes; no generated appraisal text is requested.', questions, agents)

    def advance(self, t, actions, probabilities):
        if self.pending is None or t != self.round+1:
            raise ValueError('Prepare the annual decisions first.')
        tasks = self.pending
        if self.source_ended:
            if actions:
                raise ValueError('Relocated households cannot decide.')
            event = dict(flood_event=None, grant_available=None)
        else:
            expected = {f"year{t}_{task['agent']['id']}" for task in tasks}
            if set(actions) != expected:
                raise ValueError('Decision membership changed.')
            responses = []
            for task in tasks:
                code = actions[f"year{t}_{task['agent']['id']}"]
                mapping = self.ns['DECISION_MAP_ELEVATED' if task['was_elevated'] else 'DECISION_MAP_NOT_ELEVATED']
                if code not in mapping:
                    raise ValueError('Action is not available to this household.')
                responses.append('Final Decision: '+code)
            event = self.generator.send(responses)
            if event['kind'] != 'year_end' or event['year'] != t:
                raise ValueError('Unexpected commit boundary.')
            self.agents = copy.deepcopy(event['agents'])
            self.logs = copy.deepcopy(event['logs'])
            self.actual_years = t
        self.round = t
        self.pending = None
        counts = {key: 0 for key in ('Do Nothing', 'Only Flood Insurance', 'Only House Elevation', 'Both Flood Insurance and House Elevation', 'Relocate')}
        for a in self.agents:
            counts[self.ns['classify_adaptation_state'](a)] += 1
        fresh_logs = [x for x in self.logs if x['year'] == t]
        return dict(year=t, actual_source_years=self.actual_years, source_ended=self.source_ended,
                    flood_event=event['flood_event'], grant_available=event['grant_available'],
                    active_decisions=len(actions), adaptation_counts=counts,
                    mean_trust_in_insurance=sum(a['trust_in_insurance'] for a in self.agents)/100,
                    mean_trust_in_neighbors=sum(a['trust_in_neighbors'] for a in self.agents)/100,
                    flooded_households=sum(bool(x.get('flooded_this_year')) for x in fresh_logs),
                    mean_do_nothing_probability=(sum(probabilities[f"year{t}_{task['agent']['id']}"]['3' if task['was_elevated'] else '4'] for task in tasks)/len(tasks) if tasks else None),
                    logs=fresh_logs,
                    agents=copy.deepcopy(self.agents) if t == 10 else None)


def native_reference(seed, choose, *, appraisals=False):
    """Run the original author function unchanged with offline scripted responses."""
    ns = namespace(seed, choose=choose, appraisals=appraisals)
    agents, logs, _, _, floods = ns['run_simulation']()
    return dict(agents=agents, logs=logs, flood_years=sorted(floods), prompts=ns['_model'].prompts)
