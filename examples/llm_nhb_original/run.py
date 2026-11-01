"""Bounded fresh Jev execution of the full original NHB SI B.2 tournament."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from orgabm.decision_journal import DecisionJournal
from orgabm.openrouter_reliable import ReliableOpenRouterJevEngine
from orgabm.sdk import run_simulation
from examples.jev_validation.run import Ensemble,ExactReplay,RecoverOriginalEvents
from .suite import build_cases,analyze,GreedyDecisionEngine,original_reference


def canonical(value):return json.loads(json.dumps(value,allow_nan=False))
def save(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def hashes():
    files=list(Path('examples/llm_nhb_original').glob('*.py'))+list(Path('orgabm').glob('*.py'))
    files+=list(Path('examples/jev_validation').glob('*.py'))
    return {p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--allow-paid',action='store_true');p.add_argument('--resume',action='store_true');p.add_argument('--preview',action='store_true')
    p.add_argument('--max-cost-usd',type=float,default=.20);p.add_argument('--max-requests',type=int,default=1000)
    p.add_argument('--action-policy',choices=['sample','argmax'],default='sample',
        help='Default: sample raw Jev probabilities, application T=1. argmax is a separate historical comparison.')
    a=p.parse_args()
    if a.max_cost_usd<=0 or a.max_cost_usd>.20:raise ValueError('This original320decision suite has a maximum authorized client cap ofUS$0.20.')
    if not 1<=a.max_requests<=1000:raise ValueError('Use1..1000attempted requests.')
    cases=build_cases(a.action_policy);env=Ensemble(cases,progress=True)
    plan=canonical(dict(study='Akata2025NHB-SI-B2-full-author-source-condition-set',model='typesafe/jev-1.14',
        expected_fresh_decisions=320,source_rounds=1280,total_actor_actions=2560,ordered_matches=64,free_only_matches=49,
        external_stages=300,seed=20261030,max_cost_usd=a.max_cost_usd,max_requests=a.max_requests,
        action_policy=a.action_policy,application_probability_temperature=1 if a.action_policy=='sample' else None,
        jev_api_temperature=None,original_llm_temperature=0,
        decoding_note='Raw Jev categorical sampling is the ORDO default. LLM temperature0 is not treated as a requirement to argmax a decision model.',
        source_hashes=hashes(),environment=env.describe(),claim='Decision-model substitution on an originallyLLM-driven repeated-game experiment;not full144game/human-study replication.'))
    if a.preview:print(json.dumps(plan,indent=2));return
    if not a.allow_paid:p.error('Real provider execution requires --allow-paid.')
    root=a.output.resolve();allowed=(Path.cwd()/'runs').resolve()
    if not root.is_relative_to(allowed) or root==allowed:raise ValueError('Use a new output subdirectory inside runs/.')
    if a.resume:
        frozen=json.loads((root/'plan-before-calls.json').read_text())
        if frozen!=plan:raise ValueError('Frozen original protocol/source/cap differs;cannot resume.')
        previous=json.loads((root/'verification.json').read_text())
        if previous['status']!='failed':raise ValueError('Resume only a failed attempt.')
        attempt=previous['attempt']+1;old_cost=previous['total_reported_cost_usd'];old_requests=previous['total_attempted_requests']
        old_reserve=previous.get('total_uncertain_reserve_usd',0)
        save(root/f'verification-interrupted-{attempt-1}.json',previous);journals=sorted(root.glob('calls-*/openrouter_calls.jsonl'))
    else:
        root.mkdir(parents=True,exist_ok=False);save(root/'plan-before-calls.json',plan)
        attempt=1;old_cost=0.;old_requests=0;old_reserve=0.;journals=[]
    if old_cost+old_reserve>=a.max_cost_usd or old_requests>=a.max_requests:raise ValueError('No remaining explicit client allowance.')
    provider=ReliableOpenRouterJevEngine(root/f'calls-{attempt}',model=plan['model'],cap_usd=a.max_cost_usd-old_cost-old_reserve,
        max_requests=a.max_requests-old_requests,batch_size=64,concurrency=4,max_retries=3,timeout=90)
    recovery=RecoverOriginalEvents(provider,DecisionJournal(journals))
    engine=recovery if a.action_policy=='sample' else GreedyDecisionEngine(recovery)
    report=dict(status='running',attempt=attempt,source_hashes=plan['source_hashes']);started=time.perf_counter();save(root/'verification.json',report)
    try:
        live=run_simulation(env,engine,rounds=300,seed=plan['seed'],output=root/f'live-{attempt}')
        results=env.results();save(root/'case_results.json',results);analysis=analyze(results);save(root/'analysis.json',analysis)
        tournament=cases[0]['environment'];reference=original_reference(tournament.jev_schedule,tournament.jev_prompts)
        if reference!=tournament.rows:raise AssertionError('Original authored prompts or feedback differ.')
        save(root/'source_trace.json',dict(columns=['round','source_role1','source_role2','action1','action2','points1','points2','total1','total2'],
            replacement='All source act_gpt4 actions are newJev decisions.',rows=tournament.rows))
        replay=Ensemble(build_cases(a.action_policy));offline=run_simulation(replay,ExactReplay(root/f'live-{attempt}/events.jsonl'),rounds=300,seed=plan['seed'])
        if live['metrics']!=offline['metrics'] or canonical(results)!=canonical(replay.results()):raise AssertionError('Exact-input offline replay mismatch.')
        if live['decisions']!=320:raise AssertionError('Incomplete original external-call positions.')
        report.update(status='complete',action_policy=a.action_policy,fresh_decisions_in_completed_run=320,source_rounds=1280,total_actor_actions=2560,
            ordered_matches=64,free_only_matches=49,offline_replay_all_inputs_and_metrics_exact=True,
            original_source_all1280rows_and_authored320prompts_exact=True)
    except Exception as error:report.update(status='failed',error_type=type(error).__name__,error=str(error));raise
    finally:
        usage=engine.usage();report.update(usage_this_attempt=usage,elapsed_s_this_attempt=time.perf_counter()-started,
            total_reported_cost_usd=old_cost+usage['recorded_input_cost_usd'],total_attempted_requests=old_requests+usage['attempted_requests'],
            total_uncertain_reserve_usd=old_reserve+usage.get('outstanding_or_uncertain_cost_reserve_usd',0))
        save(root/'verification.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
