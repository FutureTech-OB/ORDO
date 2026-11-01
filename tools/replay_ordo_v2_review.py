"""Verify and replay exported v2 evidence without model credentials or inference."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from orgabm.sdk import run_simulation,validate_decisions

ROOT=Path('docs/appendix_ordo_v2_evidence')


class RecordedEngine:
    def __init__(self,path):self.stream=gzip.open(path,'rt',encoding='utf-8');self.decisions=0
    def decide(self,state,questions):
        row=json.loads(next(self.stream))
        if row['state']!=state or row['questions']!=questions:raise ValueError('Saved input mismatch.')
        self.decisions+=len(questions)
        return validate_decisions(questions,row['probabilities'])
    def usage(self):return dict(recorded_input_cost_usd=0,actual_model_api_calls=0,replayed_decisions=self.decisions)
    def close(self):
        try:
            if next(self.stream,None) is not None:raise ValueError('Unconsumed evidence events.')
        finally:self.stream.close()


def read_gzip(path):
    with gzip.open(path,'rt',encoding='utf-8') as stream:return json.load(stream)


def verify_hashes():
    manifest=json.loads((ROOT/'manifest.json').read_text())
    for row in manifest['files']:
        path=(ROOT/row['path']).resolve()
        if not path.is_relative_to(ROOT.resolve()):raise ValueError('Unsafe evidence path.')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('Exported checksum mismatch.')
        value=gzip.decompress(raw) if row['compression']=='gzip' else raw
        if hashlib.sha256(value).hexdigest()!=row['uncompressed_sha256']:raise ValueError('Original-byte checksum mismatch.')
    return len(manifest['files'])


def main():
    files=verify_hashes();checks={}
    from examples.llm_abm_cookbook.behavior import make_naming_worlds
    for label in ['jev','uniform']:
        engine=RecordedEngine(ROOT/f'naming/naming-{label}-events.jsonl.gz')
        world=make_naming_worlds()
        result=run_simulation(world,engine,rounds=max(world.max_updates.values()),seed=717)
        engine.close();stored=read_gzip(ROOT/f'naming/naming-{label}-result.json.gz')
        if result['metrics']!=stored['metrics'] or result['decisions']!=stored['decisions']:
            raise ValueError('Naming replay outcome mismatch.')
        original=json.loads((ROOT/f'naming/naming-{label}-worlds.json').read_text())
        if world.summaries()!=original['worlds']:raise ValueError('Naming personal histories/summary mismatch.')
        checks['naming-'+label]=dict(decisions=result['decisions'],all_inputs_and_metrics_exact=True)
    from examples.jev_validation.run import Ensemble
    from examples.llm_original_sa.suite import build_cases as majority
    from examples.llm_nhb_original.suite import build_cases as games,original_reference
    for label,factory,rounds in [('majority',majority,500),('games',games,300)]:
        world=Ensemble(factory());engine=RecordedEngine(ROOT/f'{label}/events.jsonl.gz')
        result=run_simulation(world,engine,rounds=rounds,seed=20261030)
        engine.close();stored=read_gzip(ROOT/f'{label}/result.json.gz')
        if result['metrics']!=stored['metrics'] or result['decisions']!=stored['decisions']:
            raise ValueError('Replay outcome mismatch: '+label)
        if label=='games':
            tournament=world.cases[0]['environment']
            if tournament.rows!=original_reference(tournament.jev_schedule,tournament.jev_prompts):
                raise ValueError('Original author loop mismatch.')
        checks[label]=dict(decisions=result['decisions'],all_inputs_and_metrics_exact=True)
    report=dict(status='verified',exported_files_checked=files,cases=checks,actual_model_api_calls=0,
        polarization='partial run only; no forty-epoch completion claimed')
    (ROOT/'replay_verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
