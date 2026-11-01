"""Explicit checkpoint + exact pending-event recovery for this cookbook.

The first valid logged response is retained for its original question. Only
missing decisions are submitted, with bounded transport retries enabled.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import time

from orgabm.decision_journal import DecisionJournal,ResumeDecisionEngine
from orgabm.openrouter_reliable import ReliableOpenRouterJevEngine
from orgabm.sdk import run_simulation
from .model import OrganizationEnsemble
from .run import make_worlds,export_snapshots,save


def combined_usage(previous,new):
    result=copy.deepcopy(new)
    for key in ('attempted_requests','successful_responses','input_tokens','output_tokens','recorded_input_cost_usd'):
        result[key]=previous[key]+new[key]
    result['models_returned']=sorted(set(previous['models_returned'])|set(new['models_returned']))
    result['mean_request_latency_s']=None
    result['unsuccessful_transport_attempts']=result['attempted_requests']-result['successful_responses']
    result['prior_retry_attempts']=previous.get('retry_attempts',0)+previous.get('prior_retry_attempts',0)
    result['client_cap_usd']=3;result['client_max_requests']=6000
    result['accounting']='Successful usage.cost only; failed attempts may add unknown charges. Checkpoints and exact-event journals avoid resubmitting recorded decisions.'
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True);parser.add_argument('--allow-paid',action='store_true')
    args=parser.parse_args()
    if not args.allow_paid:parser.error('--allow-paid is required.')
    root=Path(args.run).resolve(); allowed=(Path.cwd()/'runs').resolve()
    if root==allowed or not root.is_relative_to(allowed):raise ValueError('Select a directory inside this repository\'s runs/.')
    report=json.loads((root/'verification.json').read_text(encoding='utf-8'))
    if report['status']!='failed' or report['groups'].get('jev',{}).get('status')!='failed':
        raise ValueError('Expected a failed live organizational convention experiment.')
    frozen=json.loads((root/'plan-before-calls.json').read_text(encoding='utf-8'))
    for name,sha in report['source_hashes'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=sha:raise ValueError('Recorded experiment sources changed; inspect before recovery.')
    attempt=len(report.get('recoveries',[]))+1
    trace_name=report.get('active_jev_trace','jev'); trace=root/trace_name
    previous_result=json.loads((trace/'result.json').read_text(encoding='utf-8'))
    completed=previous_result['completed_rounds']; previous=report['usage']
    journal_names=report.get('decision_journals',['calls/openrouter_calls.jsonl'])
    journal=DecisionJournal([root/p for p in journal_names])
    save(root/f'verification-interrupted-{attempt}.json',report)
    recovered_name=f'jev-recovery-{attempt}'; calls_name=f'recovery-{attempt}-calls'
    if (root/recovered_name).exists() or (root/calls_name).exists():raise ValueError('Recovery attempt output already exists.')
    # Reserve a conservative text-request allowance for older failures whose byte counts were not logged.
    old_unknown=max(0,previous['attempted_requests']-previous['successful_responses'])
    old_reserve=max(previous.get('outstanding_or_uncertain_cost_reserve_usd',0),old_unknown*32000*.042/1_000_000)
    provider=ReliableOpenRouterJevEngine(root/calls_name,cap_usd=3-previous['recorded_input_cost_usd']-old_reserve,
        max_requests=6000-previous['attempted_requests'],batch_size=32,concurrency=2,max_retries=3,timeout=90)
    worlds=make_worlds(frozen['configs']);periods=next(iter(worlds.values())).rounds
    def progress(row):
        if row['period']>completed:
            print(json.dumps(dict(engine='jev-resume',**row,usage=combined_usage(previous,provider.usage()))),flush=True)
    env=OrganizationEnsemble(worlds,progress)
    recovery=dict(attempt=attempt,completed_prefix_periods=completed,source_trace=trace_name,
        recovered_trace=recovered_name,partial_journal_entries=len(journal.entries),concurrency=2,max_retries=3,timeout_s=90)
    report.setdefault('recoveries',[]).append(recovery)
    report['active_jev_trace']=recovered_name;report['status']='resuming'
    report['source_hashes'].update({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [Path(__file__),Path('orgabm/openrouter_reliable.py'),Path('orgabm/decision_journal.py')]})
    save(root/'verification.json',report);started=time.perf_counter();engine=None
    try:
        with (trace/'events.jsonl').open(encoding='utf-8') as stream:
            engine=ResumeDecisionEngine(provider,journal,stream,completed)
            result=run_simulation(env,engine,rounds=periods,seed=202610,output=root/recovered_name)
        summary=export_snapshots(root/'jev-snapshots',worlds,env.latest)
        report['groups']['jev']=dict(status=result['status'],decisions=result['decisions'],worlds=summary)
        report['status']='complete';report.pop('error_type',None)
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__)
        report['groups']['jev']=dict(status='failed',worlds=export_snapshots(root/f'jev-partial-recovery-{attempt}',worlds,env.latest))
        raise
    finally:
        name=f'{calls_name}/openrouter_calls.jsonl'
        if (root/name).exists() and name not in journal_names:journal_names.append(name)
        report['decision_journals']=journal_names
        report['usage']=combined_usage(previous,engine.usage() if engine else provider.usage())
        recovery['elapsed_s']=time.perf_counter()-started;report['elapsed_s']+=recovery['elapsed_s']
        if engine:recovery.update(prefix_decisions=engine.prefix_decisions,partial_decisions=engine.partial_decisions,fresh_decisions=engine.fresh_decisions)
        save(root/'verification.json',report)
    print(json.dumps(dict(status=report['status'],usage=report['usage'],recovery=recovery),indent=2))


if __name__=='__main__':main()
