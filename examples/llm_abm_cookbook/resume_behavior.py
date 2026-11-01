"""Explicit recovery of an interrupted opinion phase from its exact event prefix.

Historical steps are reconstructed offline; only remaining steps call Jev.
This is a dedicated cookbook recovery helper, not general distributed recovery.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import time

from orgabm.openrouter import OpenRouterJevEngine
from orgabm.sdk import FunctionEngine,run_simulation
from .behavior import make_opinion_worlds


def save(path,value): path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


class PrefixThenLive:
    def __init__(self,stream,completed,engine,previous):
        self.stream=stream; self.completed=completed; self.engine=engine; self.previous=previous; self.step=0
    def decide(self,state,questions):
        self.step+=1
        if self.step<=self.completed:
            record=json.loads(next(self.stream))
            if state!=record['state'] or questions!=record['questions']:
                raise AssertionError('Checkpoint observations differ; no live request sent for this step.')
            return record['probabilities']
        return self.engine.decide(state,questions)
    def usage(self):
        old=self.previous; new=self.engine.usage(); total=copy.deepcopy(new)
        for field in ['attempted_requests','successful_responses','input_tokens','output_tokens','recorded_input_cost_usd']:
            total[field]=old[field]+new[field]
        total['models_returned']=sorted(set(old['models_returned'])|set(new['models_returned']))
        count=old['successful_responses']+new['successful_responses']
        total['mean_request_latency_s']=((old['mean_request_latency_s'] or 0)*old['successful_responses']+
            (new['mean_request_latency_s'] or 0)*new['successful_responses'])/count
        total.update(client_cap_usd=2.0,client_max_requests=6000,recovery_prefix_steps=self.completed,
            ambiguous_prior_failed_requests=old['attempted_requests']-old['successful_responses'],
            prior_failure_cost='unknown; may be additional to reported usage.cost',
            accounting='Successful response usage only. Explicit checkpoint recovery follows one interrupted request; no past inference is resubmitted.')
        return total


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True); parser.add_argument('--allow-paid',action='store_true')
    args=parser.parse_args()
    if not args.allow_paid: parser.error('Explicit --allow-paid is required.')
    root=Path(args.run).resolve(); allowed=(Path.cwd()/'runs').resolve()
    if root==allowed or not root.is_relative_to(allowed): raise ValueError('Use an experiment directory inside this repository\'s runs/.')
    report=json.loads((root/'verification.json').read_text(encoding='utf-8'))
    if report['status']!='failed' or 'naming' not in report['groups'] or 'opinion' in report['groups']:
        raise ValueError('Expected an interrupted first opinion phase after a complete naming phase.')
    interrupted=root/'opinion-jev'; recovered=root/'opinion-jev-recovered'; archived=root/'opinion-jev-interrupted'
    if recovered.exists() or archived.exists(): raise ValueError('Recovery output already exists; inspect before another explicit recovery.')
    original=json.loads((interrupted/'result.json').read_text(encoding='utf-8'))
    completed=original['completed_rounds']; previous=report['usage']
    (root/'verification-interrupted.json').write_bytes((root/'verification.json').read_bytes())
    engine=OpenRouterJevEngine(root/'recovery-calls',cap_usd=2-previous['recorded_input_cost_usd'],
        max_requests=6000-previous['attempted_requests'],batch_size=16,concurrency=4)
    report.update(status='resuming',recovery=dict(completed_prefix_steps=completed,interrupted_artifact='opinion-jev-interrupted',
        reason='one transport failure; response unavailable',fresh_calls_only_after_prefix=True))
    report['source_hashes'][str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    save(root/'verification.json',report); started=time.perf_counter()
    provider=None
    try:
        world=make_opinion_worlds()
        world.progress=lambda row:print(json.dumps(dict(group='opinion-recovery',**row)),flush=True) if row['step']>completed else None
        with (interrupted/'events.jsonl').open(encoding='utf-8') as stream:
            provider=PrefixThenLive(stream,completed,engine,previous)
            result=run_simulation(world,provider,rounds=1000,seed=717,output=recovered)
        paid=dict(status=result['status'],decisions=result['decisions'],worlds=world.summaries())
        save(root/'opinion-jev-worlds.json',paid)
        # All paths were resolved inside the explicitly selected runs directory above.
        interrupted.rename(archived); recovered.rename(interrupted)
        report['groups']['opinion']={'jev':paid}
        control=make_opinion_worlds()
        free=run_simulation(control,FunctionEngine(lambda s,q:{k:1/len(q['criteria']) for k in q['criteria']},
            name='uniform-random-explicit-rule'),rounds=1000,seed=717,output=root/'opinion-uniform')
        report['groups']['opinion']['uniform']=dict(status=free['status'],decisions=free['decisions'],worlds=control.summaries())
        save(root/'opinion-uniform-worlds.json',report['groups']['opinion']['uniform'])
        report['status']='complete'; report.pop('error_type',None)
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__)
        raise
    finally:
        report['usage']=provider.usage() if provider else previous
        report['recovery']['elapsed_s']=time.perf_counter()-started
        report['elapsed_s']+=report['recovery']['elapsed_s']
        save(root/'verification.json',report)
    print(json.dumps(dict(status=report['status'],usage=report['usage']),indent=2))


if __name__=='__main__': main()
