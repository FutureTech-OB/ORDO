"""Preview or run the complete 50-world WRR LLM-arm protocol with fresh Jev.

No network activity occurs without --allow-paid. Never reads a credential file.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

from orgabm.decision_journal import DecisionJournal
from orgabm.openrouter_reliable import ReliableOpenRouterJevEngine
from orgabm.sdk import run_simulation
from examples.jev_validation.run import Ensemble, ExactReplay, RecoverOriginalEvents, save

from . import suite
from .environment import UPSTREAM


def source_hashes():
    paths = list(Path(__file__).parent.rglob('*.py'))
    paths += list(UPSTREAM.glob('*'))
    paths += list(Path('orgabm').glob('*.py'))
    paths += [Path('examples/jev_validation/run.py')]
    root = Path.cwd().resolve()
    return {p.resolve().relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(set(paths)) if p.is_file()}


def payload_forecast(batch_size):
    """An offline all-inaction tape estimates wire payload, not human behavior.

No empirical decision distribution is assumed; this nonrelocating path retains
the maximum 50,000 decisions. Tokens use a rough 4-byte/token heuristic only.
"""
    stats = dict(offline_scripted_decisions=0, wire_bytes=0, requests_without_retries=0)
    def choose(state, questions):
        items = list(questions.items())
        for i in range(0, len(items), batch_size):
            body = json.dumps(dict(model='typesafe/jev-1.14', state=state,
                                   questions=dict(items[i:i+batch_size])), ensure_ascii=True).encode()
            stats['wire_bytes'] += len(body)
            stats['requests_without_retries'] += 1
        stats['offline_scripted_decisions'] += len(questions)
        return {qid:{key:float(key == ('4' if '4' in q['criteria'] else '3'))
                     for key in q['criteria']} for qid,q in questions.items()}
    class Meter:
        def decide(self,state,questions):
            return choose(state,questions)
        def usage(self):
            return dict(offline=True)
    run_simulation(Ensemble(suite.build_cases()), Meter(), rounds=10, seed=20261030)
    stats.update(heuristic_tokens_at_four_bytes_per_token=stats['wire_bytes']/4,
                 price_reference_usd_per_million_input_tokens=.042,
                 heuristic_input_cost_usd=stats['wire_bytes']/4*.042/1_000_000,
                 total_byte_based_reservation_analogue_usd=stats['wire_bytes']*.042/1_000_000,
                 caveat='Offline all-inaction sizing only, not a forecast of Jev choices or an exact token count. Relocation reduces decisions; other action paths change prompt lengths. Provider cost is measured separately.')
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='runs/llm-wrr-original-20261030')
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--allow-paid', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--max-cost-usd', type=float, default=5)
    parser.add_argument('--max-requests', type=int, default=3500)
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--concurrency', type=int, default=4)
    args = parser.parse_args()
    cases = suite.build_cases()
    ensemble = Ensemble(cases, progress=True)
    plan = dict(schema='llm_wrr_original_v1', model='typesafe/jev-1.14',
                seed=20261030, rounds=10, worlds=50, maximum_fresh_decisions=50000,
                max_cost_usd=args.max_cost_usd, max_requests=args.max_requests,
                batch_size=args.batch_size, concurrency=args.concurrency,
                source_hashes=source_hashes(), description=ensemble.describe(),
                profile='paper_fixed_flood_scenario_with_public_source_initializer',
                exact_paper_configuration=False,
                paper_source_differences=dict(
                    insurance_trust=dict(article=[.3,.6],code=[.2,.5]),
                    neighbor_trust=dict(article=[.4,.65],code=[.35,.55]),
                    initial_elevation=dict(article='randomly assigned',code=False)),
                input_availability='Complete source generator and synthetic event pool are available. Original CSV profiles, original seeds and numerical 50-run aggregate reference are not included in the public repository.',
                claim='Complete original LLM-ABM integration with fresh decision-engine substitution; not claimed reproduction of author Gemma trajectories or Figure-2 numerical outcomes.')
    if args.preview:
        plan['offline_payload_forecast'] = payload_forecast(args.batch_size)
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    if not args.allow_paid:
        parser.error('Fresh inference requires explicit --allow-paid.')
    root = Path(args.output)
    allowed = (Path.cwd()/'runs').resolve()
    if not root.resolve().is_relative_to(allowed) or root.resolve() == allowed:
        raise ValueError('Output must be a child directory of runs/.')
    if args.resume:
        frozen = json.loads((root/'plan-before-calls.json').read_text(encoding='utf-8'))
        if frozen != plan:
            raise ValueError('Protocol, source or allowance changed; cannot resume.')
        prior = json.loads((root/'verification.json').read_text(encoding='utf-8'))
        if prior['status'] != 'failed':
            raise ValueError('Only interrupted/failed attempts may resume.')
        attempt = prior['attempt']+1
        journals = sorted(root.glob('calls-*/openrouter_calls.jsonl'))
        old_cost = prior['total_reported_cost_usd']
        old_requests = prior['total_attempted_requests']
        old_reserved = prior.get('total_uncertain_reserve_usd',0)
        save(root/f'verification-interrupted-{attempt-1}.json',prior)
    else:
        root.mkdir(parents=True,exist_ok=False)
        save(root/'plan-before-calls.json',plan)
        attempt,journals,old_cost,old_requests,old_reserved = 1,[],0.,0,0.
    provider = ReliableOpenRouterJevEngine(root/f'calls-{attempt}',model=plan['model'],
        cap_usd=plan['max_cost_usd']-old_cost-old_reserved,
        max_requests=plan['max_requests']-old_requests,batch_size=plan['batch_size'],
        concurrency=plan['concurrency'],max_retries=3,timeout=90)
    engine = RecoverOriginalEvents(provider,DecisionJournal(journals))
    report = dict(status='running',attempt=attempt,source_hashes=plan['source_hashes'])
    save(root/'verification.json',report)
    started = time.perf_counter()
    try:
        live = run_simulation(ensemble,engine,rounds=10,seed=20261030,output=root/f'live-{attempt}')
        results = ensemble.results()
        save(root/'case_results.json',results)
        save(root/'analysis.json',suite.analyze(results))
        replay = Ensemble(suite.build_cases())
        offline = run_simulation(replay,ExactReplay(root/f'live-{attempt}'/'events.jsonl'),rounds=10,seed=20261030)
        if live['metrics'] != offline['metrics'] or results != replay.results():
            raise ValueError('Exact-input replay does not match.')
        if source_hashes() != plan['source_hashes']:
            raise ValueError('Frozen source changed during execution.')
        report.update(status='complete',worlds=50,years=10,
                      fresh_decisions_in_completed_run=live['decisions'],
                      offline_replay_all_inputs_and_metrics_exact=True,
                      frozen_source_unchanged=True,exact_paper_configuration=False)
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__,error=str(error))
        raise
    finally:
        usage = engine.usage()
        report.update(usage_this_attempt=usage,elapsed_s_this_attempt=time.perf_counter()-started,
                      actual_model_api_calls_this_attempt=usage['attempted_requests'],
                      total_reported_cost_usd=old_cost+usage['recorded_input_cost_usd'],
                      total_attempted_requests=old_requests+usage['attempted_requests'],
                      total_uncertain_reserve_usd=old_reserved+usage.get('outstanding_or_uncertain_cost_reserve_usd',0))
        save(root/'verification.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
