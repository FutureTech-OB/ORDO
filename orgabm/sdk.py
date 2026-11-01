"""Public experimental SDK. The ABM owns the world; engines see local questions."""
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
import copy
import hashlib
import json
import math
import time
from .randomness import sample, stable_seed


@dataclass
class DecisionBatch:
    state: str
    questions: dict
    agent_ids: dict


class Environment(Protocol):
    def describe(self) -> dict: ...
    def prepare(self, round_no: int) -> DecisionBatch: ...
    def advance(self, round_no: int, actions: dict, probabilities: dict) -> dict: ...


class DecisionEngine(Protocol):
    def decide(self, state: str, questions: dict) -> dict: ...
    def usage(self) -> dict: ...


def validate_decisions(questions, answers):
    if not isinstance(answers, dict) or set(questions) != set(answers):
        raise ValueError('Decision IDs do not match the prepared batch.')
    validated = {}
    for qid, question in questions.items():
        p = answers[qid]
        if not isinstance(p, dict) or set(p) != set(question['criteria']):
            raise ValueError('Actions do not match the allowed action set.')
        if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in p.values()):
            raise ValueError('Invalid probability value.')
        mass = sum(p.values())
        if mass <= 0 or abs(mass-1) > 0.005*len(p)+1e-9:
            raise ValueError('Invalid probability mass.')
        validated[qid] = {key: value/mass for key, value in p.items()}
    return validated


class FunctionEngine:
    """Wrap a researcher-defined rule or offline model without changing the runner."""
    def __init__(self, function, name='custom-function'):
        self.function, self.name = function, name

    def decide(self, state, questions):
        return {qid: self.function(state, q) for qid, q in questions.items()}

    def usage(self):
        return {'engine': self.name, 'recorded_input_cost_usd': 0}


def run_simulation(environment, engine, *, rounds, seed, output=None):
    """Prepare -> decide all -> validate all -> sample -> commit one synchronous round.

    A fresh environment instance is required for every run. Arbitrary Python
    adapters are trusted local code; this API is not a code execution sandbox.
    """
    if type(rounds) is not int or rounds < 1 or type(seed) is not int:
        raise ValueError('Positive integer rounds and an integer seed are required.')
    metadata = copy.deepcopy(environment.describe())
    json.dumps(metadata, allow_nan=False)
    root = Path(output) if output is not None else None
    if root:
        root.mkdir(parents=True, exist_ok=False)
    manifest = dict(schema_version='0.2', status='running', environment=metadata,
                    engine=type(engine).__name__, seed=seed, rounds=rounds,
                    probability_reuse=False, completed_rounds=0, decisions=0, metrics=[])
    started = time.perf_counter()
    seen = set()
    try:
        for t in range(1, rounds+1):
            batch = copy.deepcopy(environment.prepare(t))
            if set(batch.questions) != set(batch.agent_ids):
                raise ValueError('Every decision needs an agent identity.')
            if len(set(batch.agent_ids.values())) != len(batch.agent_ids):
                raise ValueError('An agent may have only one decision per synchronous round.')
            if seen.intersection(batch.questions):
                raise ValueError('Decision IDs must be fresh across rounds.')
            for qid, q in batch.questions.items():
                if not isinstance(qid, str) or not q.get('criteria') or not isinstance(q.get('instructions'), str):
                    raise ValueError('Invalid decision question.')
            seen.update(batch.questions)
            probabilities = validate_decisions(batch.questions, engine.decide(batch.state, copy.deepcopy(batch.questions)))
            actions = {qid: sample(p, stable_seed('action', seed, t, batch.agent_ids[qid]))
                       for qid, p in probabilities.items()}
            metrics = environment.advance(t, actions, probabilities)
            manifest['metrics'].append(metrics)
            manifest['completed_rounds'] = t
            manifest['decisions'] += len(actions)
            if root:
                record = dict(round=t, state=batch.state, questions=batch.questions,
                              agent_ids=batch.agent_ids, probabilities=probabilities,
                              actions=actions, metrics=metrics)
                with (root/'events.jsonl').open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False)+'\n')
        manifest['status'] = 'complete'
    except Exception as error:
        manifest['status'] = 'failed'
        manifest['error_type'] = type(error).__name__
        raise
    finally:
        manifest['elapsed_s'] = time.perf_counter()-started
        manifest['usage'] = engine.usage()
        manifest['sdk_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        manifest['source_hashes'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in Path(__file__).parent.glob('*.py')}
        if root:
            (root/'result.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    return manifest
