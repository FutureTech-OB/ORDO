"""Full 882-day public capsule, full-candidate fresh Jev edge scores and exact recovery."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
from orgabm.sdk import validate_decisions
from orgabm.openrouter_reliable import ReliableOpenRouterJevEngine
from .model import FullPublicColocation,NativeProbabilityEngine
from .source import digest


def save(path,value):
    target=Path(path);temporary=target.with_suffix(target.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    temporary.replace(target)


def hashes():
    base=Path.cwd().resolve()
    paths=[*Path(__file__).resolve().parent.glob('*.py'),
        base/'examples/ncs_colocation/sources.py',base/'orgabm/openrouter.py',
        base/'orgabm/openrouter_reliable.py',base/'orgabm/sdk.py']
    return {p.relative_to(base).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


class SqliteJournal:
    """Memory-bounded original-event recovery; never reuse scores across event IDs."""
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS events(qid TEXT PRIMARY KEY, fingerprint TEXT, probabilities TEXT)')
        self.db.commit()

    def add(self,state,questions,answers):
        for qid,q in questions.items():
            fingerprint=digest(dict(state=state,question=q))
            old=self.db.execute('SELECT fingerprint FROM events WHERE qid=?',(qid,)).fetchone()
            if old and old[0]!=fingerprint:raise ValueError('Original event ID changed its input.')
            self.db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?)',(qid,fingerprint,json.dumps(answers[qid],separators=(',',':'))))
        self.db.commit()

    def import_receipts(self,paths):
        count=0
        for path in paths:
            with Path(path).open(encoding='utf-8') as stream:
                for line in stream:
                    record=json.loads(line);request=record['request'];response=record['response']
                    if not response.get('model','').startswith(request['model']):raise ValueError('Unexpected source model in receipt.')
                    answers=validate_decisions(request['questions'],{k:v['probabilities'] for k,v in response['answers'].items()})
                    self.add(request['state'],request['questions'],answers);count+=len(answers)
        return count

    def recover(self,state,questions):
        found={};missing={}
        for qid,q in questions.items():
            row=self.db.execute('SELECT fingerprint,probabilities FROM events WHERE qid=?',(qid,)).fetchone()
            if row is None:missing[qid]=q
            else:
                if row[0]!=digest(dict(state=state,question=q)):raise ValueError('Recovery input fingerprint differs.')
                found[qid]=json.loads(row[1])
        return found,missing


class JournalEngine:
    def __init__(self,provider,journal):self.provider=provider;self.journal=journal;self.recovered=0;self.fresh=0
    def decide(self,state,questions):
        found,missing=self.journal.recover(state,questions);self.recovered+=len(found)
        if missing:
            if self.provider is None:raise ValueError('Offline replay has missing original events.')
            answers=self.provider.decide(state,missing)
            self.journal.add(state,missing,answers);found.update(answers);self.fresh+=len(missing)
        return {qid:found[qid] for qid in questions}


def run(world,engine,out,attempt,provider=None):
    fingerprints=[];started=time.perf_counter();source_sha=digest(hashes())
    with (out/f'stages-{attempt}.jsonl').open('w',encoding='utf-8') as events:
        for t in range(1,1765):
            batch=world.prepare(t);input_sha=digest(dict(state=batch.state,questions=batch.questions))
            answers=validate_decisions(batch.questions,engine.decide(batch.state,batch.questions))
            result=world.advance(t,{},answers)
            fingerprint=digest(result);fingerprints.append(fingerprint)
            # Full original questions/responses are in provider receipts. Compact stage tape
            # stores the input fingerprint, returned score order and actual global quota draw.
            events.write(json.dumps(dict(stage=t,source_bundle_sha256=source_sha,input_sha256=input_sha,result_sha256=fingerprint,
                probabilities=[answers[q]['contact'] for q in batch.questions],result=result),separators=(',',':'))+'\n');events.flush()
            checkpoint=dict(status='running',stage=t,total_stages=1764,completed_days=len(world.days),
                scored_events=world.score_count,selected_edges=world.selected_count,input_sha256=input_sha,
                source_bundle_sha256=source_sha,result_sha256=fingerprint,elapsed_s=time.perf_counter()-started,
                usage=provider.usage() if provider else dict(actual_api_calls=0))
            save(out/'progress.json',checkpoint)
            save(out/'checkpoint-latest.json',dict(**checkpoint,state=world.checkpoint()))
            if t==1 or t%20==0:print(json.dumps({k:checkpoint[k] for k in ['stage','completed_days','scored_events','elapsed_s']}),flush=True)
    world.finish()
    return fingerprints


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    parser.add_argument('--cache',default='.buildtmp/ncs-colocation-source')
    parser.add_argument('--preview',action='store_true');parser.add_argument('--allow-paid',action='store_true')
    parser.add_argument('--resume',action='store_true');parser.add_argument('--verify-native',action='store_true')
    parser.add_argument('--numpy-seed',type=int,default=20261030)
    parser.add_argument('--batch-size',type=int,default=512);parser.add_argument('--concurrency',type=int,default=4)
    parser.add_argument('--max-cost-usd',type=float,default=50.);parser.add_argument('--max-requests',type=int,default=12000)
    args=parser.parse_args();world=FullPublicColocation(args.cache,args.numpy_seed)
    first=world.prepare(1);items=list(first.questions.items())
    first_body_bytes=sum(len(json.dumps(dict(model='typesafe/jev-1.14',state=first.state,questions=dict(items[i:i+args.batch_size])),ensure_ascii=True).encode())
                         for i in range(0,len(items),args.batch_size))
    plan=dict(model='typesafe/jev-1.14',batch_size=args.batch_size,concurrency=args.concurrency,
        max_cost_usd=args.max_cost_usd,max_requests=args.max_requests,source_hashes=hashes(),environment=world.describe(),
        complete_stages=1764,complete_days=882,expected_candidate_score_queries=2737728,
        native_reference_realization_queries=2737667,expected_successful_http_batches=6174,
        first_stage=dict(candidates=len(first.questions),quota=world.pending[0]['size'],http_batches=math.ceil(len(first.questions)/args.batch_size),request_body_bytes=first_body_bytes),
        estimated_total_request_bytes=first_body_bytes/len(first.questions)*2737728,
        budget='The explicit CLI client allowance bounds reported cost and conservative reservations. Preview byte arithmetic is not a price quote; actual usage.cost is authoritative.',
        throughput='1764 dependent stages; about 6174 successful HTTP batches at batch512/concurrency4. Measure first stage; no small proxy replaces the full plan.',
        sampling='Same original global quotas and without-replacement draw; all first-stage candidates and all remaining second-stage candidates separately scored. No candidate cap.',
        recovery='Exact original event fingerprint via SQLite; restore by replaying completed original events, including partial-batch receipts. No probability reuse for new events.')
    if args.preview:
        print(json.dumps(plan,ensure_ascii=False,indent=2));return
    if not args.verify_native and not args.allow_paid:parser.error('--allow-paid is required for live inference.')
    out=Path(args.output);allowed=(Path.cwd()/'runs').resolve()
    if not out.resolve().is_relative_to(allowed) or out.resolve()==allowed:raise ValueError('Choose an output subdirectory in runs/.')
    # Rebuild since preview preparation intentionally did not commit a first-stage draw.
    world=FullPublicColocation(args.cache,args.numpy_seed)
    old_cost=old_reserve=0.;old_requests=0
    if args.resume:
        frozen=json.loads((out/'plan-before-calls.json').read_text(encoding='utf-8'))
        protocol=lambda p:{k:v for k,v in p.items() if k not in ('max_cost_usd','max_requests')}
        if protocol(frozen)!=protocol(plan):raise ValueError('Source, scientific protocol or data changed; recovery refused.')
        old=json.loads((out/'verification.json').read_text(encoding='utf-8'))
        if old['status']=='complete':raise ValueError('This run is already complete.')
        attempt=old['attempt']+1;old_cost=old['total_reported_cost_usd'];old_reserve=old['total_uncertain_reserve_usd'];old_requests=old['total_attempted_requests']
        save(out/f'verification-interrupted-{attempt-1}.json',old)
        prior_limits=old.get('current_client_limits',dict(max_cost_usd=frozen['max_cost_usd'],max_requests=frozen['max_requests']))
        current_limits=dict(max_cost_usd=args.max_cost_usd,max_requests=args.max_requests)
        if prior_limits!=current_limits:
            save(out/f'budget-revision-attempt-{attempt}.json',dict(previous=prior_limits,revised=current_limits,
                scientific_protocol_unchanged=True,source_bundle_sha256=digest(plan['source_hashes']),
                reason='Explicit CLI budget revision; completed original events are recovered exactly, with no change to full 882-day target.'))
    else:
        out.mkdir(parents=True,exist_ok=False);save(out/'plan-before-calls.json',plan);attempt=1
    journal=SqliteJournal(out/'original-events.sqlite')
    if args.resume:journal.import_receipts(sorted(out.glob('calls-*/openrouter_calls.jsonl')))
    provider=None if args.verify_native else ReliableOpenRouterJevEngine(out/f'calls-{attempt}',model=plan['model'],
        cap_usd=args.max_cost_usd-old_cost-old_reserve,max_requests=args.max_requests-old_requests,
        batch_size=args.batch_size,concurrency=args.concurrency,max_retries=3,timeout=90)
    engine=NativeProbabilityEngine(world) if args.verify_native else JournalEngine(provider,journal)
    report=dict(status='running',attempt=attempt,scope=plan['environment']['scope'],private_full_mit_data_missing=True,
        total_reported_cost_usd=old_cost,total_uncertain_reserve_usd=old_reserve,total_attempted_requests=old_requests,
        current_client_limits=dict(max_cost_usd=args.max_cost_usd,max_requests=args.max_requests))
    started=time.perf_counter();save(out/'verification.json',report)
    try:
        live=run(world,engine,out,attempt,provider)
        save(out/'daily_metrics.json',world.days);save(out/'phase_results.json',world.phases)
        if args.verify_native:
            original=json.loads(Path('runs/ncs-original-colocation-20261030/native_results.json').read_text(encoding='utf-8'))
            # Compare ordered raw graph series of both complete branches.
            actual={'remote_then_return':digest(world.graphs[:467]),'continuous_colocation':digest(world.graphs[:52]+world.graphs[467:])}
            checks={name:sha==original['path_metrics'][name]['graph_series_sha256'] for name,sha in actual.items()}
            if not all(checks.values()):raise AssertionError('Full staged source kernel differs from author reference.')
            report.update(native_reference_checks=checks)
        else:
            rebuilt=FullPublicColocation(args.cache,args.numpy_seed)
            offline=run(rebuilt,JournalEngine(None,journal),out,f'{attempt}-offline',None)
            if live!=offline:raise AssertionError('Full original-input offline replay differs from live transitions.')
            report.update(offline_all_stage_inputs_and_state_metrics_exact=True,
                fresh_decisions_this_attempt=engine.fresh,recovered_original_decisions=engine.recovered)
        report.update(status='complete',native_days=len(world.days),complete_stages=world.round,
            scored_edge_events=world.score_count,selected_edges=world.selected_count)
    except BaseException as error:
        report.update(status='failed',error_type=type(error).__name__,error=str(error));raise
    finally:
        usage=provider.usage() if provider else dict(actual_api_calls=0)
        report.update(usage_this_attempt=usage,elapsed_s_this_attempt=time.perf_counter()-started,
            completed_stages=world.round,completed_days=len(world.days),scored_events=world.score_count,
            total_reported_cost_usd=old_cost+usage.get('recorded_input_cost_usd',0),
            total_uncertain_reserve_usd=old_reserve+usage.get('outstanding_or_uncertain_cost_reserve_usd',0),
            total_attempted_requests=old_requests+usage.get('attempted_requests',0))
        save(out/'verification.json',report)
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
