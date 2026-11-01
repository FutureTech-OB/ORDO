"""Run independent paper-derived worlds with fresh, natively batched Jev inference.

Each question contains only its own world's permitted context. Event recovery
reuses an already returned answer only for the exact original event/input.
"""
import argparse
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time

from orgabm.decision_journal import DecisionJournal
from orgabm.openrouter_reliable import ReliableOpenRouterJevEngine
from orgabm.sdk import DecisionBatch, run_simulation, validate_decisions


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


class Ensemble:
    def __init__(self, cases, progress=False):
        self.cases = cases
        ids = [c['id'] for c in cases]
        if not cases or len(ids) != len(set(ids)):
            raise ValueError('A nonempty set of unique case IDs is required.')
        self.pending = {}
        self.metrics = {c['id']: [] for c in cases}
        self.decisions = {c['id']: 0 for c in cases}
        self.progress = progress

    def describe(self):
        return dict(scenario='fresh_jev_paper_validation', cases=[dict(
            id=c['id'], paper_id=c['paper_id'], rounds=c['rounds'], seed=c['seed'],
            condition=c['condition'], environment=c['environment'].describe()) for c in self.cases],
            batch_semantics='independent ready decisions; each question embeds only its local context',
            action_sampling='SDK stable seed with namespaced actor IDs; not paired common random numbers',
            probability_reuse=False)

    def prepare(self, t):
        self.pending = {}
        questions, agents = {}, {}
        for c in self.cases:
            if t > c['rounds']:
                continue
            batch = c['environment'].prepare(t)
            names = {f"{c['id']}::{q}": q for q in batch.questions}
            for scoped, qid in names.items():
                question = copy.deepcopy(batch.questions[qid])
                question['instructions'] = ('Local context for this decision:\n' + batch.state
                    + '\n\n' + question['instructions'])
                questions[scoped] = question
                agents[scoped] = f"{c['id']}::{batch.agent_ids[qid]}"
            self.pending[c['id']] = names
        return DecisionBatch(
            'These are separate independent participant decisions. Use only the local context of each question.',
            questions, agents)

    def advance(self, t, actions, probabilities):
        out = {}
        for c in self.cases:
            if c['id'] not in self.pending:
                continue
            names = self.pending[c['id']]
            a = {qid: actions[scoped] for scoped, qid in names.items()}
            p = {qid: probabilities[scoped] for scoped, qid in names.items()}
            result = c['environment'].advance(t, a, p)
            self.metrics[c['id']].append(copy.deepcopy(result))
            self.decisions[c['id']] += len(a)
            out[c['id']] = result
        if self.progress and (t == 1 or t % 20 == 0):
            print(json.dumps(dict(period=t, decisions=sum(self.decisions.values()))), flush=True)
        return out

    def results(self):
        return [dict(id=c['id'], paper_id=c['paper_id'], seed=c['seed'], condition=c['condition'],
            result=dict(status='complete', environment=c['environment'].describe(),
                rounds=c['rounds'], completed_rounds=len(self.metrics[c['id']]),
                decisions=self.decisions[c['id']], metrics=self.metrics[c['id']])) for c in self.cases]


class ExactReplay:
    def __init__(self, path):
        self.rows = iter(Path(path).read_text(encoding='utf-8').splitlines())
        self.count = 0

    def decide(self, state, questions):
        row = json.loads(next(self.rows))
        if row['state'] != state or row['questions'] != questions:
            raise ValueError('Offline replay inputs differ from the live experiment.')
        self.count += len(questions)
        return validate_decisions(questions, row['probabilities'])

    def usage(self):
        return dict(recorded_input_cost_usd=0, offline_replayed_decisions=self.count)


class RecoverOriginalEvents:
    def __init__(self, provider, journal):
        self.provider, self.journal = provider, journal
        self.recovered = self.fresh = 0

    def decide(self, state, questions):
        found, missing = self.journal.recover(state, questions)
        self.recovered += len(found)
        if missing:
            found.update(self.provider.decide(state, missing))
            self.fresh += len(missing)
        return found

    def usage(self):
        return dict(self.provider.usage(), original_events_recovered=self.recovered,
                    fresh_decisions_this_attempt=self.fresh)


def source_hashes(group):
    paths = list(Path(f'examples/jev_{group}').glob('*.py'))
    paths += list(Path('examples/jev_validation').glob('*.py'))
    paths += list(Path(f'examples/jev_{group}').glob('*.json'))
    paths += list(Path('orgabm').glob('*.py'))
    base = Path.cwd().resolve()
    for module in list(sys.modules.values()):
        file = getattr(module, '__file__', None)
        if file:
            path = Path(file).resolve()
            if path.suffix == '.py' and path.is_relative_to(base/'examples'):
                paths.append(path.relative_to(base))
    return {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=['nc', 'ncs', 'sa'], required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--allow-paid', action='store_true')
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--max-cost-usd', type=float, default=2)
    parser.add_argument('--max-requests', type=int, default=2500)
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--concurrency', type=int, default=4)
    args = parser.parse_args()
    module = importlib.import_module(f'examples.jev_{args.group}.suite')
    cases = module.build_cases()
    ensemble = Ensemble(cases, progress=True)
    plan = dict(group=args.group, model='typesafe/jev-1.14', seed=20261030,
        max_cost_usd=args.max_cost_usd, max_requests=args.max_requests,
        batch_size=args.batch_size, concurrency=args.concurrency,
        rounds=max(c['rounds'] for c in cases), source_hashes=source_hashes(args.group),
        description=ensemble.describe(), claim='fresh decision-model substitution; phenomenon tests, not full-paper replication')
    if args.preview:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    if not args.allow_paid:
        parser.error('Explicit --allow-paid is required for fresh Jev inference.')
    root = Path(args.output)
    allowed = (Path.cwd()/'runs').resolve()
    if not root.resolve().is_relative_to(allowed) or root.resolve() == allowed:
        raise ValueError('Choose an output subdirectory inside runs/.')
    if args.resume:
        frozen = json.loads((root/'plan-before-calls.json').read_text(encoding='utf-8'))
        if frozen != plan:
            raise ValueError('The declared protocol, source files or allowance changed; cannot resume.')
        prior = json.loads((root/'verification.json').read_text(encoding='utf-8'))
        if prior['status'] != 'failed':
            raise ValueError('Only failed attempts can be resumed.')
        attempt = prior['attempt'] + 1
        journals = sorted(root.glob('calls-*/openrouter_calls.jsonl'))
        old_cost = prior['total_reported_cost_usd']
        old_requests = prior['total_attempted_requests']
        old_reserved = prior.get('total_uncertain_reserve_usd', 0)
        save(root/f'verification-interrupted-{attempt-1}.json', prior)
    else:
        root.mkdir(parents=True, exist_ok=False)
        save(root/'plan-before-calls.json', plan)
        attempt, journals, old_cost, old_requests, old_reserved = 1, [], 0., 0, 0.
    provider = ReliableOpenRouterJevEngine(root/f'calls-{attempt}', model=plan['model'],
        cap_usd=plan['max_cost_usd']-old_cost-old_reserved,
        max_requests=plan['max_requests']-old_requests, batch_size=plan['batch_size'],
        concurrency=plan['concurrency'], max_retries=3, timeout=90)
    engine = RecoverOriginalEvents(provider, DecisionJournal(journals))
    report = dict(status='running', group=args.group, attempt=attempt,
        actual_model_api_calls_this_attempt=0, source_hashes=plan['source_hashes'])
    started = time.perf_counter()
    save(root/'verification.json', report)
    try:
        live = run_simulation(ensemble, engine, rounds=plan['rounds'], seed=plan['seed'],
                              output=root/f'live-{attempt}')
        results = ensemble.results()
        save(root/'case_results.json', results)
        analysis = module.analyze(results) if hasattr(module, 'analyze') else dict(cases=results)
        save(root/'analysis.json', analysis)
        replay = Ensemble(module.build_cases())
        offline = run_simulation(replay, ExactReplay(root/f'live-{attempt}'/'events.jsonl'),
                                 rounds=plan['rounds'], seed=plan['seed'])
        if live['metrics'] != offline['metrics'] or results != replay.results():
            raise ValueError('Full-input offline replay does not match the live run.')
        report.update(status='complete', paper_ids=sorted({c['paper_id'] for c in cases}),
            worlds=len(cases), fresh_decisions_in_completed_run=live['decisions'],
            offline_replay_all_inputs_and_metrics_exact=True, analysis=analysis)
    except Exception as error:
        report.update(status='failed', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        usage = engine.usage()
        report.update(usage_this_attempt=usage, elapsed_s_this_attempt=time.perf_counter()-started,
            actual_model_api_calls_this_attempt=usage['attempted_requests'],
            total_reported_cost_usd=old_cost+usage['recorded_input_cost_usd'],
            total_attempted_requests=old_requests+usage['attempted_requests'],
            total_uncertain_reserve_usd=old_reserved+usage.get('outstanding_or_uncertain_cost_reserve_usd', 0))
        save(root/'verification.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
