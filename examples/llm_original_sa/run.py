"""Fresh Jev run of the complete De Marzo Fig.2 N=50 experimental condition."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from orgabm.sdk import run_simulation
from orgabm.decision_journal import DecisionJournal
from orgabm.openrouter_reliable import ReliableOpenRouterJevEngine
from examples.jev_validation.run import Ensemble,ExactReplay,RecoverOriginalEvents
from .suite import build_cases,analyze


def save(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def source_hashes():
    paths=[*Path(__file__).resolve().parent.glob('*.py'),Path('examples/jev_validation/run.py').resolve(),
           Path('orgabm/sdk.py').resolve(),Path('orgabm/randomness.py').resolve(),Path('orgabm/decision_journal.py').resolve(),
           Path('orgabm/openrouter.py').resolve(),Path('orgabm/openrouter_reliable.py').resolve()]
    base=Path.cwd().resolve()
    return {p.relative_to(base).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    p.add_argument('--preview',action='store_true');p.add_argument('--allow-paid',action='store_true');p.add_argument('--resume',action='store_true')
    p.add_argument('--max-cost-usd',type=float,default=1.);p.add_argument('--max-requests',type=int,default=2000)
    p.add_argument('--batch-size',type=int,default=20);p.add_argument('--concurrency',type=int,default=4)
    args=p.parse_args();cases=build_cases();ensemble=Ensemble(cases,progress=True)
    plan=dict(experiment='demarzo_2026_fig2_N50_complete_condition',figure='Fig.2, N50/m0=0/t10 arm with Jev replacing the language model',
        model='typesafe/jev-1.14',worlds=20,agents=50,max_population_time=10,max_updates_per_world=500,
        maximum_fresh_decisions=10000,model_api_temperature=None,source_llm_temperature=.2,
        seed=20261030,batch_size=args.batch_size,concurrency=args.concurrency,
        max_cost_usd=args.max_cost_usd,max_requests=args.max_requests,source_hashes=source_hashes(),
        description=ensemble.describe(),scope='Complete original condition and original independent repetition count; a new model arm, not all original models or paper-wide replication.',
        benchmark='All 20 endpoint coordination values, consensus count, censored t<=10, first-consensus times and actual provider-reported cost. Reference files are comparison data only, never inference engines.')
    assert json.loads(json.dumps(plan,allow_nan=False))==plan
    if args.preview:print(json.dumps(plan,ensure_ascii=False,indent=2));return
    if not args.allow_paid:p.error('--allow-paid is required for actual inference.')
    root=Path(args.output);allowed=(Path.cwd()/'runs').resolve()
    if not root.resolve().is_relative_to(allowed) or root.resolve()==allowed:raise ValueError('Use an output subdirectory in runs/.')
    old_cost=old_reserve=0.;old_requests=0
    if args.resume:
        frozen=json.loads((root/'plan-before-calls.json').read_text(encoding='utf-8'))
        science=lambda x:{k:v for k,v in x.items() if k not in ('max_cost_usd','max_requests')}
        if science(frozen)!=science(plan):raise ValueError('Original protocol/source changed; cannot recover.')
        prior=json.loads((root/'verification.json').read_text(encoding='utf-8'))
        if prior['status']=='complete':raise ValueError('The experiment is already complete.')
        attempt=prior['attempt']+1;old_cost=prior['total_reported_cost_usd'];old_reserve=prior['total_uncertain_reserve_usd'];old_requests=prior['total_attempted_requests']
        save(root/f'verification-interrupted-{attempt-1}.json',prior)
        if args.max_cost_usd!=frozen['max_cost_usd'] or args.max_requests!=frozen['max_requests']:
            save(root/f'budget-revision-{attempt}.json',dict(original=dict(cost=frozen['max_cost_usd'],requests=frozen['max_requests']),
                revised=dict(cost=args.max_cost_usd,requests=args.max_requests),scientific_protocol_unchanged=True))
    else:
        root.mkdir(parents=True,exist_ok=False);save(root/'plan-before-calls.json',plan);attempt=1
    provider=ReliableOpenRouterJevEngine(root/f'calls-{attempt}',model=plan['model'],cap_usd=args.max_cost_usd-old_cost-old_reserve,
        max_requests=args.max_requests-old_requests,batch_size=args.batch_size,concurrency=args.concurrency,max_retries=3,timeout=90)
    engine=RecoverOriginalEvents(provider,DecisionJournal(sorted(root.glob('calls-*/openrouter_calls.jsonl'))))
    report=dict(status='running',attempt=attempt,scope=plan['scope'],source_hashes=plan['source_hashes'])
    started=time.perf_counter();save(root/'verification.json',report)
    try:
        live=run_simulation(ensemble,engine,rounds=500,seed=plan['seed'],output=root/f'live-{attempt}')
        results=ensemble.results();summary=analyze(results)
        save(root/'case_results.json',results);save(root/'analysis.json',summary)
        rebuilt=Ensemble(build_cases())
        replay=run_simulation(rebuilt,ExactReplay(root/f'live-{attempt}/events.jsonl'),rounds=500,seed=plan['seed'])
        if live['metrics']!=replay['metrics'] or results!=rebuilt.results():raise ValueError('Full-input replay differs.')
        report.update(status='complete',fresh_decisions_in_completed_run=live['decisions'],complete_original_worlds=20,
            offline_all_original_inputs_and_metrics_exact=True,analysis=summary)
    except BaseException as error:
        report.update(status='failed',error_type=type(error).__name__,error=str(error));raise
    finally:
        usage=engine.usage();report.update(usage_this_attempt=usage,elapsed_s_this_attempt=time.perf_counter()-started,
            total_reported_cost_usd=old_cost+usage['recorded_input_cost_usd'],
            total_uncertain_reserve_usd=old_reserve+usage.get('outstanding_or_uncertain_cost_reserve_usd',0),
            total_attempted_requests=old_requests+usage['attempted_requests'])
        save(root/'verification.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
