"""Sequential decision stages with a barrier inside each stage.

Stages are committed independently. A failed later stage stops the run and keeps
earlier stage evidence; it never marks the partially executed round complete.
"""
import copy
import hashlib
import json
from pathlib import Path
import time
from typing import Protocol
from .sdk import DecisionBatch, validate_decisions
from .randomness import sample, stable_seed


class StagedEnvironment(Protocol):
    def describe(self) -> dict: ...
    def stages(self, round_no: int) -> list: ...
    def prepare_stage(self, round_no: int, stage: str) -> DecisionBatch: ...
    def advance_stage(self, round_no: int, stage: str, actions: dict, probabilities: dict) -> dict: ...
    def finish_round(self, round_no: int) -> dict: ...


def run_staged_simulation(environment, engine, *, rounds, seed, output=None):
    if type(rounds) is not int or rounds < 1 or type(seed) is not int:
        raise ValueError('Positive integer rounds and an integer seed required.')
    root = Path(output) if output is not None else None
    if root:
        root.mkdir(parents=True, exist_ok=False)
    result = dict(schema_version='0.5', status='running', environment=copy.deepcopy(environment.describe()),
                  engine=type(engine).__name__, seed=seed, rounds=rounds, completed_rounds=0,
                  completed_stages=0, decisions=0, probability_reuse=False, metrics=[])
    json.dumps(result, allow_nan=False)
    seen, started = set(), time.perf_counter()

    def log(record):
        if root:
            with (root/'events.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False)+'\n')

    try:
        for t in range(1, rounds+1):
            stages = environment.stages(t)
            if (not isinstance(stages, list) or not stages or
                any(not isinstance(s, str) or not s for s in stages) or len(set(stages)) != len(stages)):
                raise ValueError('Stages must be distinct nonempty names in causal order.')
            for stage in stages:
                result['active_round'], result['active_stage'] = t, stage
                batch = copy.deepcopy(environment.prepare_stage(t, stage))
                if set(batch.questions) != set(batch.agent_ids) or len(set(batch.agent_ids.values())) != len(batch.agent_ids):
                    raise ValueError('Each stage permits one decision per agent with an explicit identity.')
                if seen.intersection(batch.questions):
                    raise ValueError('Every stage decision needs a fresh ID.')
                for qid, question in batch.questions.items():
                    if not isinstance(qid, str) or not question.get('criteria') or not isinstance(question.get('instructions'), str):
                        raise ValueError('Invalid stage decision.')
                seen.update(batch.questions)
                probabilities = validate_decisions(batch.questions, engine.decide(batch.state, copy.deepcopy(batch.questions))) if batch.questions else {}
                actions = {q: sample(p, stable_seed('stage_action', seed, t, stage, batch.agent_ids[q])) for q,p in probabilities.items()}
                effects = environment.advance_stage(t, stage, actions, probabilities)
                result['decisions'] += len(actions)
                result['completed_stages'] += 1
                log(dict(event='stage', round=t, stage=stage, state=batch.state, questions=batch.questions,
                         agent_ids=batch.agent_ids, probabilities=probabilities, actions=actions, effects=effects))
            metrics = environment.finish_round(t)
            result['metrics'].append(metrics)
            result['completed_rounds'] = t
            log(dict(event='round', round=t, metrics=metrics))
        result['status'] = 'complete'
    except Exception as error:
        result.update(status='failed', error_type=type(error).__name__)
        raise
    finally:
        result['usage'] = engine.usage()
        result['elapsed_s'] = time.perf_counter()-started
        result['source_hashes'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}
        if root:
            (root/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    return result
