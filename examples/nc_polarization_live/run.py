"""Run the main-figure-size Gun Control hybrid arm (1000 people, 40 epochs)."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from orgabm.sdk import run_simulation
from orgabm.decision_journal import DecisionJournal
from orgabm.openrouter_reliable import ReliableOpenRouterJevEngine
from examples.jev_validation.run import RecoverOriginalEvents,ExactReplay
from .content import ContentGenerator
from .protocol import HybridPolarization,AuthorPrompts,load_initial,metrics
from .sources import load_sources


def save(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def hashes():
    paths=[*Path('examples/nc_polarization_live').glob('*.py'),*Path('examples/nc_polarization_live').glob('*.json'),
        Path('examples/nc_polarization/archive.py'),Path('examples/jev_validation/run.py'),
        *[Path('orgabm')/n for n in ('sdk.py','randomness.py','openrouter.py','openrouter_reliable.py','decision_journal.py')]]
    return {p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


class ProgressWorld(HybridPolarization):
    def __init__(self,*args,output=None,**kwargs):super().__init__(*args,**kwargs);self.output=output
    def advance(self,t,actions,probabilities):
        m=super().advance(t,actions,probabilities)
        if self.output:
            save(self.output/'progress.json',dict(step=t,total_stages=121,metrics=m,
                content_usage=self.generator.usage()))
            if m['phase'] in ('seed_stance','speak'):
                save(self.output/'trajectory.json',self.trajectory)
                save(self.output/'latest_state.json',dict(step=t,users=self.users))
            print(json.dumps({k:m[k] for k in ('epoch','phase','neutral_share','polarization','stage_decisions')}),flush=True)
        return m


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    p.add_argument('--cache',default='.buildtmp/nc-polarization-code');p.add_argument('--download',action='store_true')
    p.add_argument('--allow-paid',action='store_true');p.add_argument('--preview',action='store_true');p.add_argument('--resume',action='store_true')
    p.add_argument('--jev-cap-usd',type=float,default=10);p.add_argument('--content-cap-usd',type=float,default=40)
    p.add_argument('--workers',type=int,default=32);p.add_argument('--jev-concurrency',type=int,default=8)
    p.add_argument('--reasoning',choices=['off','low','medium','high'],default='low')
    a=p.parse_args();source=load_sources(a.cache,a.download);snapshot=load_initial(a.cache)
    prompts=AuthorPrompts(Path(a.cache)/'utils.py')
    plan=dict(study_doi='10.1038/s41467-026-78228-y',arm='baseline Gun Control, new hybrid model',
        population=1000,epochs=40,independent_worlds=1,seed=20261030,stages=121,
        jev_model='typesafe/jev-1.14',content_model='deepseek/deepseek-v4.1-flash-1017',content_temperature=1,
        content_reasoning=a.reasoning,content_max_tokens=256 if a.reasoning=='off' else 4096,
        jev_cap_usd=a.jev_cap_usd,content_cap_usd=a.content_cap_usd,workers=a.workers,jev_concurrency=a.jev_concurrency,
        upstream=source,source_hashes=hashes(),initial_metrics=metrics(snapshot),
        scope='One full main-figure-size condition, not all topics/models/interventions or source repetitions.',
        no_future_archive_inputs=True,probability_reuse=False,
        criterion='Compare direction and trajectory of mean absolute opinion, neutral share and network homophily to baseline archive; successful execution alone is not behavioral replication.',
        adapter=HybridPolarization(snapshot,prompts,None).describe())
    if a.preview:print(json.dumps(plan,ensure_ascii=False,indent=2));return
    if not a.allow_paid:p.error('--allow-paid required for actual paid inference.')
    root=Path(a.output);allowed=Path('runs').resolve()
    if root.resolve()==allowed or not root.resolve().is_relative_to(allowed):raise ValueError('Choose a new directory under runs/.')
    if a.resume:
        frozen=json.loads((root/'plan-before-calls.json').read_text(encoding='utf-8'))
        if frozen!=plan:raise ValueError('Frozen protocol, source or allowances changed.')
        prior=json.loads((root/'verification.json').read_text(encoding='utf-8'))
        if prior['status']=='complete':raise ValueError('Run is already complete.')
        attempt=prior['attempt']+1;old=prior['total_usage'];save(root/f'verification-interrupted-{attempt-1}.json',prior)
    else:
        root.mkdir(parents=True,exist_ok=False);save(root/'plan-before-calls.json',plan);attempt=1
        old=dict(jev_cost=0,jev_reserve=0,content_cost=0,content_reserve=0)
    content=ContentGenerator(root/f'content-{attempt}',reasoning=a.reasoning,cap_usd=a.content_cap_usd-old['content_cost']-old['content_reserve'],
        journals=sorted(root.glob('content-*/content_calls.jsonl')))
    provider=ReliableOpenRouterJevEngine(root/f'calls-{attempt}',model=plan['jev_model'],cap_usd=a.jev_cap_usd-old['jev_cost']-old['jev_reserve'],
        batch_size=64,concurrency=a.jev_concurrency,max_requests=20000,max_retries=3,timeout=90)
    engine=RecoverOriginalEvents(provider,DecisionJournal(sorted(root.glob('calls-*/openrouter_calls.jsonl'))))
    world=ProgressWorld(snapshot,prompts,content,seed=plan['seed'],workers=a.workers,output=root)
    report=dict(status='running',attempt=attempt,total_usage=old,source_hashes=plan['source_hashes'])
    save(root/'verification.json',report);start=time.perf_counter()
    try:
        live=run_simulation(world,engine,rounds=plan['stages'],seed=plan['seed'],output=root/f'live-{attempt}')
        content_offline=ContentGenerator(root/'offline-content',reasoning=a.reasoning,journals=sorted(root.glob('content-*/content_calls.jsonl')),offline=True)
        rebuilt=HybridPolarization(snapshot,prompts,content_offline,seed=plan['seed'],workers=a.workers)
        replay=run_simulation(rebuilt,ExactReplay(root/f'live-{attempt}/events.jsonl'),rounds=plan['stages'],seed=plan['seed'])
        if live['metrics']!=replay['metrics'] or world.users!=rebuilt.users:raise ValueError('Full hybrid replay differs.')
        save(root/'trajectory.json',world.trajectory)
        report.update(status='complete',fresh_decision_events=live['decisions'],final_metrics=world.current_metrics(),
            cumulative_counts=world.counts,offline_all_inputs_text_actions_and_final_state_exact=True,
            behavioral_replication_status='pending independent analysis against held-out author trajectory')
    except BaseException as error:
        report.update(status='failed',error_type=type(error).__name__,error=str(error));raise
    finally:
        ju=engine.usage();cu=content.usage()
        report.update(jev_usage_this_attempt=ju,content_usage_this_attempt=cu,elapsed_s_this_attempt=time.perf_counter()-start,
            total_usage=dict(jev_cost=old['jev_cost']+ju['recorded_input_cost_usd'],
                jev_reserve=old['jev_reserve']+ju['outstanding_or_uncertain_cost_reserve_usd'],
                content_cost=old['content_cost']+cu['recorded_input_cost_usd'],
                content_reserve=old['content_reserve']+cu['outstanding_or_uncertain_cost_reserve_usd']))
        save(root/'verification.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
